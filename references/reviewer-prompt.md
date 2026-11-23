# Independent reviewer: instructions

(Claude copies this into each reviewer's prompt and fills in the packet path, the mode and where to save the findings.)

You are an independent reviewer checking a screenplay that another Claude reformatted. You did not do the
work, so don't assume it's right. Read the packet file at **{PACKET}** (mode: **{MODE}**). It has the ORIGINAL
text of some pages and the FORMATTED elements for those pages.

The rule the work had to follow: **format only, never rewrite.** Every word of the original must be
present, in order, and nothing may be added, apart from these allowed format changes:
- casing (CAPS headings and names, sentence-case dialogue)
- `SCENE 4` moving to the margins, and `CUT` → `CUT TO:`
- (CONT'D)
- a short bracketed note moved under the next speaker's name
- a long bracketed description turned into an action line with the brackets removed
- a sentence split by a page break joined back together

Check, line by line against the original:
1. **Missing or extra content:** any original line, sentence, speech or scene not among the formatted
   elements, or anything formatted that isn't in the original. (A word-check script already ran, so
   focus on whole lines in the wrong place, duplicated lines, and page edges.)
2. **Wrong element type:** dialogue tagged as action, a parenthetical given to the wrong speaker, a
   scene heading missed or invented, a character name that isn't a speaker.
3. **Wrong speaker:** a speech attached to a different character than in the original.
4. **Scene headings:** `INT./EXT. LOCATION - TIME` in caps, with the writer's location words unchanged.
5. **Telugu (modes te/full):** each `⇒` line must be the *same words written in Telugu letters, as spoken*.
   Flag any word that was **translated** instead of transliterated (e.g. daddy → నాన్న is wrong; it should
   be డాడీ), any dropped or added word, misspellings of common Telugu words, wrong word breaks, and
   `(MISSING TELUGU)`. In full mode every non-character line needs Telugu. Character names stay English.
6. **V3 (mode v3)**: same Telugu rules as full mode, **plus** every character must have a Telugu
   `⇒ name:` (spoken spelling, e.g. KARTHIK → కార్తీక్), and lines marked `[V3: printed beside the next speech]`
   must really lead into that speech (the action happening as it's said, or setting it up). A long or unrelated
   action marked beside, or a short lead-in left on its own row where it clearly belongs to the speech,
   is kind `v3-layout`.

7. **V4 (mode v4)**: there is no Telugu. The formatted text must be the writer's own words in English letters,
   exactly as in the original (same spelling, even where it looks like a typo). Flag any Telugu script, any
   changed, translated or "corrected" word, and any speaker name that differs from the original. Lines marked
   `[V4: printed beside the next speech]` follow the same beside-the-speech rule as V3 (kind `v3-layout`).

Only report real problems; matters of taste are not problems. Don't edit any files.
Save your findings as JSON to **{OUT}**, as a list (an empty list `[]` if everything is right):

```json
[{"element": 25, "page": 3, "kind": "telugu-translated", "problem": "“daddy” written as నాన్న", "fix": "డాడీ"}]
```

`kind` is one of: `missing`, `extra`, `wrong-type`, `wrong-speaker`, `heading`, `telugu-translated`,
`telugu-spelling`, `telugu-missing`, `v3-layout`, `other`. Use `"element": null` for a missing line and say which
original page it's on. Then reply with one line: the number of findings.
