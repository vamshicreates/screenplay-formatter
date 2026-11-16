---
name: "screenplay-formatter"
description: "Reformat a film script from the user's folder into standard screenplay format (.docx + .pdf) without changing a word, cross-checked page by page with independent review; Telugu modes: dialogue (V1), whole script (V2), or the Telugu two-column crew layout (V3)."
---

# Screenplay Formatter

The user points to a script file (PDF, DOCX, TXT or Fountain) in their Claude folder. It is not in
professional screenplay format. You produce a new version in industry-standard format, **with the
writer's words exactly as they are**. You change format, never content.

Four modes:
- **Standard** (default): formatted .docx + .pdf.
- **Telugu V1 — dialogue only** (user asks for Telugu dialogue / Telugu letters / "version 1"): same,
  but every dialogue line written in Telugu script. This is a change of script, not a translation.
- **Telugu V2 — full Telugu** (user asks for "complete/full Telugu", "everything in Telugu",
  "version 2"): title page, scene headings, action, parentheticals, transitions and dialogue all in
  Telugu letters, same words. Only the character names above dialogue stay English CAPS
  (KARTHIK, SUGUNA, and (CONT'D)/(V.O.) with them). Names inside action and dialogue go into Telugu letters.
- **Telugu V3 — two-column crew layout** (user asks for "version 3", "V3", "two-column", "Telugu
  format like our scripts"): the layout Telugu film crews use. Scene-heading bar in English, bold
  (`4.INT    KARTHIK ROOM/HALL    -DAY/MORNING`); below it, action in Telugu letters in the left column and
  `name :` + dialogue in the right columns. Character names are in **Telugu letters** too (`సుగుణ :`). An
  action that leads into a speech sits beside it on the same row, and short tone notes (parentheticals) go
  there too, without brackets. Same Telugu text as V2.
  If the user says just "Telugu" and it's unclear which, ask V1, V2 or V3. If they don't mention Telugu,
  make the standard version only and offer the Telugu versions in one line.

## The golden rule: modify, don't rewrite

Allowed (format only):
- Deciding what each line is (scene heading, action, character, parenthetical, dialogue, transition)
- Line breaks, indents, spacing, joining a sentence that a page break split in two
- Casing: headings and character names in CAPS; ALL-CAPS dialogue → sentence case; first appearance of
  a character in action in CAPS; parentheticals lowercase
- Heading punctuation: `SCENE 4 INT. HALL -DAY` → `INT. HALL - DAY` with `4` in the scene-number margins;
  `INT/EXT` → `INT./EXT.`
- `CUT` → `CUT TO:`, `FADE IN` → `FADE IN:`; `(CONT'D)` added automatically by the renderer
- Removing the brackets from a long bracketed description that is really action; moving a short
  bracketed tone/action note from above a speaker's name to under it
- Removing a colon after a character name

Never: add, remove, replace, reorder or "fix" words. Don't correct spelling or grammar, don't add
FADE IN, don't add scene numbers that weren't there, don't merge or split scenes. Possible typos go in
the notes for the user, unchanged in the script.

## Where the files live

Helper scripts and fonts live next to this file (`scripts/`, `fonts/`, `references/`). On the author's machine
that is `~/Documents/Claude/skills/screenplay-formatter/` (a clone of github.com/vamshicreates/screenplay-formatter);
use wherever the user cloned it.
Run them in the cloud workspace (it has pdftotext, tesseract, LibreOffice, python-docx):

1. `device_list_dir` the user's folder to find the script they named (ask only if it's truly ambiguous).
2. `device_stage_files` the script file, every file in `skills/screenplay-formatter/scripts/`,
   `references/reviewer-prompt.md`, and the 4 fonts in `skills/screenplay-formatter/fonts/`.
3. Setup (once per session):
   ```bash
   SK=/mnt/user-data/uploads/Claude/skills/screenplay-formatter   # staged location
   mkdir -p ~/.fonts && cp $SK/fonts/*.ttf ~/.fonts/ && fc-cache -f
   pip install -q --break-system-packages indic_transliteration 2>/dev/null || true
   mkdir -p ~/work/checks && cd ~/work && cp "<staged script file>" .
   ```
   If the skill folder is missing on the user's computer, tell the user and stop. Don't rebuild the
   scripts from memory.

## Cross-checks: nothing is delivered until all of them pass

Long scripts are where pages and lines go missing, so every run has four cross-checks plus a report:

| # | Check | Catches |
|---|---|---|
| 1 | `page_check.py`: every page of the original was read | scanned or image pages, blank pages, pages lost in extraction (OCR'd automatically) |
| 2 | `check_fidelity.py`: every word, page by page | dropped, added, changed or reordered words; speeches out of order |
| 3 | `check_output.py`: re-reads the finished .docx and .pdf | anything lost while making the files; Telugu missing from a line |
| 4 | Independent reviewers (one per packet of pages) | wrong line types, wrong speaker, misplaced lines, translated or misspelled Telugu |
| | `report.py` → `<name> - check report.txt` | a page-by-page ✓ table and every flag, fix and decision, delivered with the files |

If a check fails, fix `script.json` (never the source) and run the checks again from step 4. Check 4 is skipped
only when the user says "skip review" or "quick draft". In that case, say so in the report and the reply.

## Steps

Make a task list: extract → page check → draft → review → word check → (Telugu) → render → file check
→ independent review → report → look at pages → deliver.

**1. Extract** — `python3 $SK/scripts/extract_text.py "<file>" source.txt`

**2. Page check (cross-check 1)** — `python3 $SK/scripts/page_check.py "<file>" source.txt --report checks/pages.json`
- The PDF page count must equal the pages read. Scanned pages are OCR'd automatically, and the OCR text replaces
  that page in `source.txt`. View every `OCR` page image (`pdftoppm -r 80 -png -f N -l N`) and correct the
  OCR text in `source.txt` where it misread. OCR is English letters only.
- `UNREAD` (an image page OCR couldn't read, e.g. Telugu-script or handwritten): view the page image and type
  its text into that page of `source.txt` yourself, then re-run. It must PASS before you go on.
- `LOW` / `blank`: view the page image and confirm it really has little or no text.

**3. Draft** — `python3 $SK/scripts/draft_parse.py source.txt draft.json`
(`--keep-case` if the user wants dialogue casing left as is.) This guesses each element's type.

**4. Review (your judgement, the important step).** Read `source.txt` in full and view the PDF's pages
(`pdftoppm -r 60 -png`) where the layout is unclear. For long scripts, go through it in chunks of about
10 pages so no page is skimmed. Go through `draft.json` element by element and write `script.json`:
- Fix wrong types. A line written as `NAME: text` is a character + dialogue. A short all-caps line with
  deep indent followed by text is a cue in standard input.
- Bracketed text: short (about ≤ 6 words), about how the *next* speaker talks or acts → parenthetical
  under that speaker's name. Longer, or about other people / the scene → action line, brackets removed.
- Join action broken mid-sentence by a page break; keep separate paragraphs the writer meant as separate.
- Proper nouns inside dialogue after sentence-casing (names, brands, quoted titles like "Iron-Man").
- Scene headings: `INT.`/`EXT.`/`INT./EXT.` + LOCATION + ` - ` + TIME, all caps. Keep the writer's
  location words exactly (including typos).
- Remove every `flag` key once handled. Put the user-facing points in `"notes"`: judgement calls
  (what moved where), anything joined, and possible typos left unchanged.
- Leave a title page as given (`title_page.title`, `center` lines, `contact` lines). If the source has
  no title page, set `title_page` to null.
- Set `"no_contd": true` on a character element only if (CONT'D) would be wrong (e.g. a new scene the
  renderer can't see).

**5. Word check (cross-check 2)** — `python3 $SK/scripts/check_fidelity.py source.txt script.json --report checks/fidelity.json`
It must print PASS, with every page ✓. It compares every word in order (case and punctuation ignored)
and the sequence of speakers, and names the page of each difference. On FAIL, fix `script.json` (you
dropped, added or changed a word) and re-run. Never edit the source to make it pass.

**6. Telugu V1 (dialogue only).**
- `python3 $SK/scripts/telugu.py export script.json dialogue.json` and read it.
- Write `te.json` (`{"<index>": "<Telugu>"}`) by the spelling rules below. For long scripts, do it in
  batches of about 60 lines.
- `cp script.json script_te.json && python3 $SK/scripts/telugu.py merge script_te.json te.json`
- `python3 $SK/scripts/telugu.py check script_te.json --report checks/telugu-te.json`: must PASS (no missing lines, no English letters
  left). Look at each REVIEW item: word-count changes must only come from fixing an obvious typo,
  and "sounds different" items must be loanwords, not translations. Add each typo you corrected to `notes`.

**6b. Telugu V2 (full Telugu)** — same three commands, each with `--all`, on `script_full.json`:
```bash
python3 $SK/scripts/telugu.py export script.json lines.json --all      # every element except character names, plus title page (keys tp.title, tp.center.N, tp.contact.N)
cp script.json script_full.json && python3 $SK/scripts/telugu.py merge script_full.json te_full.json --all
python3 $SK/scripts/telugu.py check script_full.json --all --report checks/telugu-full.json
```
The Telugu check also fails on broken letters (a vowel sign with no letter before it, which prints as ◌).

**6c. Telugu V3 (two-column)**: start from `script_full.json` (do 6b first), then save `script_v3.json` with:
- `"names_te"`: every character name in Telugu letters, spoken spelling (`{"KARTHIK": "కార్తీక్", "DANCE TEACHER": "డాన్స్ టీచర్"}`).
- `"v3_beside": true` on each action that leads straight into the next speech: what the speaker is doing as
  they say it, or a short lead-in naming them ("Ready avvutunna Karthik" → KARTHIK; "…gamanistunna SUGUNA" →
  SUGUNA). Leave long scene-setting paragraphs and action unrelated to the next speaker on their own rows.
  Parentheticals always go beside their speech automatically.
- `python3 $SK/scripts/telugu.py check script_v3.json --all --report checks/telugu-full.json` (this also checks
  `names_te`). The words are the same as V2, so no extra word check is needed.
If V1 was already done, reuse its dialogue lines in `te_full.json` so both versions match.
Scene headings: INT. → ఇంటీరియర్. · EXT. → ఎక్స్టీరియర్. · INT./EXT. → ఇంటీరియర్./ఎక్స్టీరియర్.; location and time as sounds
(ROOM/HALL - DAY/MORNING → రూమ్/హాల్ - డే/మార్నింగ్). Transitions: CUT TO: → కట్ టు:, FADE IN: → ఫేడ్ ఇన్:. Fully English action
sentences are written as sounds too ("while Satyam is feeding" → "వైల్ సత్యం ఈజ్ ఫీడింగ్"). Keep
the scene numbers (4, 7A) as they are; they print in the margins. Phone numbers, emails and URLs on the title page stay as written.

**7. Render**
```bash
python3 $SK/scripts/render.py script.json "out/<name> - formatted.docx" --pdf
python3 $SK/scripts/render.py script_te.json "out/<name> - formatted (Telugu).docx" --telugu --pdf   # Telugu V1
python3 $SK/scripts/render.py script_full.json "out/<name> - formatted (Full Telugu).docx" --telugu-full --pdf   # Telugu V2
python3 $SK/scripts/render.py script_v3.json "out/<name> - formatted (V3).docx" --v3 --pdf   # Telugu V3
```
`--no-scene-numbers` if the original had no scene numbers and the user doesn't want them (the
renderer only prints numbers that exist in the JSON anyway).

**8. Final-file check (cross-check 3)**, once for each version made:
```bash
python3 $SK/scripts/check_output.py script.json "out/<name> - formatted.docx" --mode en --report checks/output-en.json
python3 $SK/scripts/check_output.py script_te.json "out/<name> - formatted (Telugu).docx" --mode te --report checks/output-te.json
python3 $SK/scripts/check_output.py script_full.json "out/<name> - formatted (Full Telugu).docx" --mode full --report checks/output-full.json
python3 $SK/scripts/check_output.py script_v3.json "out/<name> - formatted (V3).docx" --mode v3 --report checks/output-v3.json
```
It re-opens the .docx and compares it paragraph by paragraph (V3: row by row of the two-column table) with
the JSON, then compares the PDF's letters with the .docx. A failure names the exact missing or changed
paragraph or row. V3 also fails if any script line doesn't land in exactly one row, or a name has no Telugu.
Re-render and re-check.

**9. Independent review (cross-check 4).** Reviewers check your work without having seen it being done.
- Make the packets from the richest version you produced (V3 > full Telugu > V1 > standard). That one review
  covers the shared English text and dialogue of the others:
  ```bash
  python3 $SK/scripts/review_packets.py source.txt <script_v3.json|script_full.json|script_te.json|script.json> checks/fidelity.json review --mode <v3|full|te|en> --pages 12
  ```
  Run `check_fidelity.py ... --report` first on that same JSON (it gives each element's page).
- Spawn **one reviewer per packet, all at once**, with the Agent tool (`subagent_type: general-purpose`,
  `model: opus`; the reviewer seat never gets a cheaper model). Each reviewer's prompt is
  `references/reviewer-prompt.md` with `{PACKET}`, `{MODE}` and `{OUT}` (= `review/findings_NN.json`) filled in.
- For every finding: check it against the original yourself. Real problems get fixed in the JSON. Anything
  else gets rejected with a one-line reason. Write `checks/review.json`:
  `{"reviewers": N, "packets": ["pages 1–12", ...], "findings": [{...finding..., "action": "fixed"|"rejected", "note": "..."}]}`
- If anything was fixed, re-run steps 5–8 for the affected versions. If a packet had more than about 5 real
  problems, give that packet to a fresh reviewer once more.

**10. Report** — `python3 $SK/scripts/report.py checks "out/<name> - check report.txt" --title "<name>"`
OVERALL must say ALL CHECKS PASSED. If something truly can't pass (e.g. a page is unreadable even to
you), deliver anyway, but say so plainly at the top of your reply and in the report.

**11. Look at it.** `pdftoppm -r 70 -png` the PDF and view the title page plus a few script pages
(more for long scripts: first, middle, last). Check indents, that names and dialogue stay together,
that headings aren't stranded at page bottoms, and in Telugu that letters join properly (no dotted
circles ◌). Fix and re-render if needed.

**12. Deliver.** Write the files and the check report next to the original with `device_commit_files`
(never overwrite the original), e.g. `True Love Ai Workflow/sample script - formatted.pdf`. Reply briefly:
where the files are, the cross-check result in one line (e.g. "all 4 checks passed, 120/120 pages ✓, 2
reviewers, 3 fixes"), and the notes (judgement calls, typos left as written, Telugu typo fixes).

## Format spec (what render.py produces)

US Letter, Courier New 12 pt (the PDF uses Courier Prime, same spacing), 6 lines per inch, about 55 lines
per page. Margins: left 1.5", right 1", top and bottom 1". Page numbers top right ("2."), none on the title
page or the first script page.

| Element | Position (from page edge) | Notes |
|---|---|---|
| Scene heading | 1.5" | CAPS, scene number at 0.75" and the right edge; 2 blank lines before |
| Action | 1.5" – 7.5" | 1 blank line before |
| Character | 3.7" | CAPS, (V.O.)/(O.S.)/(CONT'D) after the name |
| Parenthetical | 3.1" – 5.6" | lowercase, under the name |
| Dialogue | 2.5" – 6.0" | Telugu: Noto Sans Telugu 13 pt, 18 pt line pitch (in V2 every Telugu line uses this) |
| Transition | right-aligned to 7.5" | CAPS, ends with ":" |

Name, parenthetical and dialogue are never split across pages. Headings and names keep with the next line.

**V3 (two-column):** US Letter, margins left 0.8", right 0.6", Arial 11 pt for English plus Noto Sans Telugu
12 pt, 17 pt line pitch, page numbers top right ("3", no dot), no (CONT'D). Heading bar: bold, `4.INT` at the left,
location centred, `-TIME` at the right. Body: a borderless 3-column table per scene — action 2.95" | `name :`
1.3" right-aligned | dialogue the rest. A row never splits across pages, and `CUT TO:` (Telugu) sits at the bottom
right of the scene's last row, so it can't be stranded on the next page.

## Telugu spelling rules (Tinglish → Telugu letters)

- **Transliterate, never translate.** Each word is written as it is *spoken*, in Telugu script. English
  words stay English words written in Telugu letters: office → ఆఫీస్, daddy → డాడీ, good morning →
  గుడ్ మార్నింగ్, college → కాలేజ్, night → నైట్, gate → గేట్. Never swap in a Telugu equivalent
  (daddy is never నాన్న).
- **Use the standard spelling of the intended Telugu word**, not a letter-by-letter mapping:
  vachhadu → వచ్చాడు, chesadu → చేశాడు, telusaa → తెలుసా, ekkuva → ఎక్కువ, thaalam → తాళం,
  dosa → దోశ, andi → అండి, garu → గారు, veedu → వీడు, amma → అమ్మ.
  Long vowels: aa → ా, ee/ii → ీ, oo/uu → ూ, ai → ై, au → ౌ. Doubled consonants → ఒత్తు (amma → అమ్మ).
  t/th, d/dh and l/ḷ, n/ṇ are ambiguous in Tinglish: pick the real word's spelling (thaalam → తాళం,
  koduku → కొడుకు).
- **Keep the writer's word boundaries** (`college ki` → `కాలేజ్ కి`, `nanna ni` → `నాన్న ని`) so the
  check can compare word for word.
- **Obvious typos** (a letter missing or swapped, e.g. "samasakram" for సంస్కారం): write the intended word
  and list it in notes. If you can't tell what was meant, transliterate as written and flag it.
- Keep all punctuation, ellipses, `?`/`!` runs, quotes and digits exactly (500 stays 500).
- Names: Karthik → కార్తీక్, Suguna → సుగుణ, Satyam → సత్యం (spoken spelling).
- V1: only dialogue changes. Scene headings, action, character names (English CAPS) and parentheticals stay as they are.
- V3: same Telugu text as V2, plus the character names in Telugu letters; scene headings stay English.
- V2: everything changes except the character names above dialogue. The same rules apply to every line:
  same words, sounds not translation, standard spelling of the intended word, the writer's word boundaries,
  punctuation and digits unchanged (500rs → 500రూ).
