---
name: "screenplay-formatter"
description: "Reformat a film script from the user's folder into standard screenplay format (.docx + .pdf) without changing a word; Telugu modes write the dialogue (V1) or the whole script (V2) in Telugu letters."
---

# Screenplay Formatter

The user points to a script file (PDF, DOCX, TXT or Fountain) in their Claude folder. It is not in
professional screenplay format. You produce a new version in industry-standard format, **with the
writer's words exactly as they are**. You change format, never content.

Three modes:
- **Standard** (default): formatted .docx + .pdf.
- **Telugu V1 — dialogue only** (user asks for Telugu dialogue / Telugu letters / "version 1"): same,
  but every dialogue line written in Telugu script. This is a change of script, not a translation.
- **Telugu V2 — full Telugu** (user asks for "complete/full Telugu", "everything in Telugu",
  "version 2"): title page, scene headings, action, parentheticals, transitions and dialogue all in
  Telugu letters, same words. Only the character names above dialogue stay English CAPS
  (KARTHIK, SUGUNA, and (CONT'D)/(V.O.) with them). Names inside action and dialogue go into Telugu letters.
  If the user says just "Telugu" and it's unclear which, ask V1 or V2. If they don't mention Telugu,
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

Helper scripts and fonts live next to this file (`scripts/`, `fonts/`). On the author's machine that is
`~/Documents/Claude/skills/screenplay-formatter/` (a clone of github.com/vamshicreates/screenplay-formatter);
use wherever the user cloned it.
Run them in the cloud workspace (it has pdftotext, LibreOffice, python-docx):

1. `device_list_dir` the user's folder to find the script they named (ask only if it's truly ambiguous).
2. `device_stage_files` the script file, every file in `skills/screenplay-formatter/scripts/`, and the 4
   fonts in `skills/screenplay-formatter/fonts/`.
3. Setup (once per session):
   ```bash
   SK=/mnt/user-data/uploads/Claude/skills/screenplay-formatter   # staged location
   mkdir -p ~/.fonts && cp $SK/fonts/*.ttf ~/.fonts/ && fc-cache -f
   pip install -q --break-system-packages indic_transliteration 2>/dev/null || true
   mkdir -p ~/work && cd ~/work && cp "<staged script file>" .
   ```
   If the skill folder is missing on the user's computer, tell the user and stop — don't rebuild the
   scripts from memory.

## Steps

Make a task list: extract → draft → review → fidelity check → (Telugu) → render → look at pages → deliver.

**1. Extract** — `python3 $SK/scripts/extract_text.py "<file>" source.txt`
If it warns the PDF has almost no text (scanned), OCR it with the pdf skill first.

**2. Draft** — `python3 $SK/scripts/draft_parse.py source.txt draft.json`
(`--keep-case` if the user wants dialogue casing left as is.) This guesses each element's type.

**3. Review (your judgement — the important step).** Read `source.txt` in full and view the PDF's pages
(`pdftoppm -r 60 -png`) where the layout is unclear. Go through `draft.json` element by element
and write `script.json`:
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

**4. Fidelity check** — `python3 $SK/scripts/check_fidelity.py source.txt script.json`
Must print PASS. It compares every word in order (case and punctuation ignored) and the sequence of
speakers. On FAIL, fix `script.json` (you dropped, added or changed a word) and re-run. Never edit
the source to make it pass.

**5. Telugu mode only.**
- `python3 $SK/scripts/telugu.py export script.json dialogue.json` and read it.
- Write `te.json` (`{"<index>": "<Telugu>"}`) by the spelling rules below. For long scripts, do it in
  batches of about 60 lines.
- `cp script.json script_te.json && python3 $SK/scripts/telugu.py merge script_te.json te.json`
- `python3 $SK/scripts/telugu.py check script_te.json`: must PASS (no missing lines, no English letters
  left). Look at each REVIEW item: word-count changes must only come from fixing an obvious typo,
  and "sounds different" items must be loanwords, not translations. Add each typo you corrected to `notes`.

**5b. Telugu V2 (full Telugu)** — same three commands, each with `--all`, on `script_full.json`:
```bash
python3 $SK/scripts/telugu.py export script.json lines.json --all      # every element except character names, plus title page (keys tp.title, tp.center.N, tp.contact.N)
cp script.json script_full.json && python3 $SK/scripts/telugu.py merge script_full.json te_full.json --all
python3 $SK/scripts/telugu.py check script_full.json --all
```
If V1 was already done, reuse its dialogue lines in `te_full.json` so both versions match.
Scene headings: INT. → ఇంటీరియర్. · EXT. → ఎక్స్టీరియర్. · INT./EXT. → ఇంటీరియర్./ఎక్స్టీరియర్.; location and time as sounds
(ROOM/HALL - DAY/MORNING → రూమ్/హాల్ - డే/మార్నింగ్). Transitions: CUT TO: → కట్ టు:, FADE IN: → ఫేడ్ ఇన్:. Fully English action
sentences are written as sounds too ("while Satyam is feeding" → "వైల్ సత్యం ఈజ్ ఫీడింగ్"). Keep
the scene numbers (4, 7A) as they are; they print in the margins. Phone numbers, emails and URLs on the title page stay as written.

**6. Render**
```bash
python3 $SK/scripts/render.py script.json "out/<name> - formatted.docx" --pdf
python3 $SK/scripts/render.py script_te.json "out/<name> - formatted (Telugu).docx" --telugu --pdf   # Telugu V1
python3 $SK/scripts/render.py script_full.json "out/<name> - formatted (Full Telugu).docx" --telugu-full --pdf   # Telugu V2
```
`--no-scene-numbers` if the original had no scene numbers and the user doesn't want them (the
renderer only prints numbers that exist in the JSON anyway).

**7. Look at it.** `pdftoppm -r 70 -png` the PDF and view the title page plus a few script pages
(more for long scripts: first, middle, last). Check indents, that names and dialogue stay together,
that headings aren't stranded at page bottoms, and in Telugu that letters join properly (no dotted
circles ◌). Fix and re-render if needed.

**8. Deliver.** Write the files next to the original with `device_commit_files` (never overwrite the
original), e.g. `True Love Ai Workflow/sample script - formatted.pdf`. Reply briefly: where the files
are, that the word check passed, and the notes (judgement calls + typos left as written).

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
- V2: everything changes except the character names above dialogue. The same rules apply to every line:
  same words, sounds not translation, standard spelling of the intended word, the writer's word boundaries,
  punctuation and digits unchanged (500rs → 500రూ).
