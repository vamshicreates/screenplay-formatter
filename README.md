# Screenplay Formatter — a Claude skill

Point Claude at a rough film script and get back a **properly formatted screenplay** (.docx + .pdf)
with **every word exactly as the writer wrote it**. It changes the format, never the content.

Made for Telugu filmmakers who write in *Tinglish* (Telugu written in English letters), so it can also
write the script in **Telugu letters**. That's transliteration, not translation.

| Mode | What you get |
|---|---|
| **Standard** | Industry-standard screenplay format, original words |
| **Telugu V1: dialogue only** | Same, with every dialogue line in Telugu letters (`Karthik ready aa?` → `కార్తీక్ రెడీ ఆ?`) |
| **Telugu V2: full Telugu** | Everything in Telugu letters (title page, scene headings, action, parentheticals, transitions, dialogue). Only the character names above dialogue stay in English CAPS |

---

## How to use it

Once the skill is installed (see below), just ask Claude in plain words:

```
Format the script in my "True Love Ai Workflow" folder.
Format sample script.pdf and give me the Telugu version 1.
Format the script in <folder> in full Telugu (version 2).
```

Claude will:

1. **Read** the script (PDF, DOCX, TXT or Fountain).
2. **Work out each line's type**: scene heading, action, character, parenthetical, dialogue or transition.
3. **Reformat** it to spec: scene numbers in the margins, `INT./EXT. LOCATION - TIME`, names in caps
   above dialogue, (CONT'D), `CUT TO:`, page numbers, and a title page.
4. **Run a word check** that compares every word with the original, in order. It must pass before anything is delivered.
5. **(Telugu modes)** Write the Telugu, then check that no English letters are left and that it's word for word
   with no translation.
6. **Save** `<name> - formatted.docx/.pdf`, plus `(Telugu)` or `(Full Telugu)`, **next to the original**.
   The original is never touched.
7. **Report** the judgement calls it made, and possible typos it saw but left unchanged.

### What changes and what never changes

✅ **Format only:** layout, indents, line breaks, CAPS for headings and names, ALL-CAPS dialogue → sentence case,
`SCENE 4 INT. HALL -DAY` → `INT. HALL - DAY` (with 4 in the margins), `CUT` → `CUT TO:`, short bracketed notes moved under
the speaker's name, long bracketed descriptions turned into action lines, sentences broken by a page break joined back.

❌ **Never:** adding, removing, reordering or "fixing" words. Spelling mistakes stay as written and are listed in the notes.
(In the Telugu modes, an obvious typo is written as the intended Telugu word and listed in the notes.)

### Telugu spelling rules (short version)

- **Sounds, not meaning:** `daddy` → డాడీ (never నాన్న), `office` → ఆఫీస్, `good morning` → గుడ్ మార్నింగ్.
- **Standard spelling of the intended word:** `vachhadu` → వచ్చాడు, `thaalam` → తాళం.
- **The writer's word breaks, punctuation and digits stay the same:** `college ki` → కాలేజ్ కి, `500` stays 500.
- **V2 scene headings:** `INT. KARTHIK ROOM/HALL - DAY/MORNING` → `ఇంటీరియర్. కార్తీక్ రూమ్/హాల్ - డే/మార్నింగ్`.

---

## Install

**1. Get the files** into your Claude folder:

```bash
cd ~/Documents/Claude/skills
git clone https://github.com/vamshicreates/screenplay-formatter.git
```

**2. Add the skill to Claude:** in Claude, open your skills settings and upload `SKILL.md`, or ask Claude to
"save this skill" from the file. The scripts and fonts stay in the cloned folder, and Claude loads them from there.

**3. Connect the folder:** use the Claude desktop app with your `~/Documents/Claude` folder connected,
so Claude can read your scripts and save the formatted files next to them.

Requirements (Claude's cloud workspace already has these): Python 3, `pdftotext` (poppler), LibreOffice,
`python-docx`; optional `indic_transliteration` for the Telugu sound-alike check.

---

## Format spec

US Letter · Courier New 12 pt (the PDF uses Courier Prime, same spacing) · 6 lines per inch · margins: left 1.5", right 1", top/bottom 1".

| Element | From page edge | Notes |
|---|---|---|
| Scene heading | 1.5" | CAPS, scene number at 0.75" and at the right edge |
| Action | 1.5" – 7.5" | |
| Character | 3.7" | CAPS, (CONT'D) added automatically |
| Parenthetical | 3.1" – 5.6" | |
| Dialogue | 2.5" – 6.0" | Telugu: Noto Sans Telugu 13 pt |
| Transition | right-aligned | `CUT TO:` |

A name, its parenthetical and its dialogue never split across pages. Page numbers go top right, with none on the title page or the first page of the script.

---

## Run the scripts yourself (without Claude)

```bash
SK=~/Documents/Claude/skills/screenplay-formatter
python3 $SK/scripts/extract_text.py "my script.pdf" source.txt   # 1. text out of the file
python3 $SK/scripts/draft_parse.py source.txt draft.json          # 2. first-pass guess of each line's type
#   → review draft.json by hand and save it as script.json (this is the step Claude does)
python3 $SK/scripts/check_fidelity.py source.txt script.json      # 3. must print PASS
python3 $SK/scripts/render.py script.json "my script - formatted.docx" --pdf
# Telugu: telugu.py export/merge/check (add --all for V2), then render with --telugu or --telugu-full
```

| Script | Job |
|---|---|
| `extract_text.py` | PDF/DOCX/TXT/Fountain → layout-preserving text |
| `draft_parse.py` | Heuristic first pass → structured JSON (scene headings, cues, parentheticals, merges) |
| `check_fidelity.py` | Word-for-word check against the original, plus the order of speakers |
| `telugu.py` | Export lines to write in Telugu, merge them back, check (no Latin left, same word count, sound-alike) |
| `render.py` | JSON → screenplay .docx (+ .pdf through LibreOffice); `--telugu`, `--telugu-full` |

Fonts in `fonts/` (Courier Prime, Noto Sans Telugu) are under the SIL Open Font License. See the OFL files.
For the exact look in Word, install [Noto Sans Telugu](https://fonts.google.com/noto/specimen/Noto+Sans+Telugu).

---

Built by [Vamshi Creates](https://vamshicreates.tech) · code under the MIT License.
