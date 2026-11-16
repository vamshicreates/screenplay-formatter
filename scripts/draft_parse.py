#!/usr/bin/env python3
"""Heuristic first pass: source.txt -> draft.json (structured screenplay elements).

Usage: draft_parse.py <source.txt> <draft.json> [--keep-case]

This is only a DRAFT. Claude must review every element against the source and
fix judgement calls (see SKILL.md, step 4) before rendering. Words are never
changed here — only element type, line joins, casing and heading punctuation.

Element types: scene_heading, action, character, parenthetical, dialogue,
transition. Each element may carry "flag" (a note for Claude to review).
"""
import json, re, sys

PAGE_NUM = re.compile(r"^\s*\(?\d{1,3}\)?\s*\.?\s*$")
HEAD = re.compile(
    r"^\s*(?:SCENE\s*[-:#]?\s*(?P<num>\d+[A-Z]?)\s*[.:)\-]?\s*)?"
    r"(?P<ie>INT\.?\s*/\s*EXT|EXT\.?\s*/\s*INT|I\s*/\s*E|INT|EXT)\b\.?\s*(?P<rest>.*)$",
    re.I | re.S,
)
SCENE_ONLY = re.compile(r"^\s*SCENE\s*[-:#]?\s*(?P<num>\d+[A-Z]?)\s*[.:)\-]?\s*(?P<rest>.*)$", re.I | re.S)
TRANS = re.compile(
    r"^\s*(?P<t>CUT|CUT TO|SMASH CUT(?: TO)?|MATCH CUT(?: TO)?|JUMP CUT(?: TO)?|CUT BACK TO|DISSOLVE(?: TO)?|"
    r"FADE IN|FADE OUT|FADE TO BLACK|FADE TO|INTERCUT|BACK TO)\s*[:.]*\s*$",
    re.I,
)
INLINE_CUE = re.compile(r"^(?P<name>[A-Z][A-Z0-9 .'&\-]{0,34}?)\s*(?P<ext>\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D|CONTD)\))?\s*:\s*(?P<rest>.*)$", re.S)
TIMES = ["EARLY MORNING", "LATE NIGHT", "MOMENTS LATER", "CONTINUOUS", "MORNING", "AFTERNOON", "EVENING", "NIGHT",
         "DAY", "DAWN", "DUSK", "SUNRISE", "SUNSET", "LATER", "NOON", "MIDNIGHT", "SAME"]


def norm_ie(ie):
    s = re.sub(r"[\s.]", "", ie.upper())
    return {"INT": "INT.", "EXT": "EXT.", "INT/EXT": "INT./EXT.", "EXT/INT": "EXT./INT.", "I/E": "INT./EXT."}.get(s, s + ".")


def split_loc_time(rest_lines):
    """rest_lines: list of raw strings (first line keeps column gaps)."""
    first = rest_lines[0]
    cont = " ".join(l.strip() for l in rest_lines[1:])
    m = re.search(r"\s+-+\s*|\s*-+\s+|\s+[–—]\s*", first)
    if m:
        loc, time = first[: m.start()], first[m.end():]
    else:
        cols = re.split(r"\s{3,}", first.strip())
        if len(cols) >= 2:
            loc, time = " ".join(cols[:-1]), cols[-1]
        else:
            loc, time = first, ""
            up = first.strip().upper()
            for t in TIMES:
                if up.endswith(" " + t):
                    loc, time = first.strip()[: -len(t)], first.strip()[-len(t):]
                    break
    time = (time.strip() + " " + cont).strip()
    loc = re.sub(r"\s+", " ", loc).strip(" -–—.")
    time = re.sub(r"\s+", " ", time).strip(" -–—.")
    return loc.upper(), time.upper()


def blocks_from(text):
    """Return list of blocks: dict(lines=[raw], indent=int, page=int)."""
    blocks, cur, page = [], [], 1
    for raw in text.split("\n"):
        parts = raw.split("\f")
        for i, part in enumerate(parts):
            if i > 0:
                if cur:
                    blocks.append(dict(lines=cur, page=page)); cur = []
                page += 1
            if PAGE_NUM.match(part) and part.strip():
                continue
            if part.strip() == "":
                if cur:
                    blocks.append(dict(lines=cur, page=page)); cur = []
            else:
                cur.append(part.rstrip())
    if cur:
        blocks.append(dict(lines=cur, page=page))
    for b in blocks:
        b["indent"] = min(len(l) - len(l.lstrip()) for l in b["lines"])
        b["text"] = re.sub(r"\s+", " ", " ".join(l.strip() for l in b["lines"])).strip()
    return blocks


def sentence_case(s, names):
    """ALL-CAPS dialogue -> sentence case; character names title-cased."""
    letters = [c for c in s if c.isalpha() and c.isascii()]
    if not letters or sum(c.isupper() for c in letters) / len(letters) < 0.8:
        return s  # already mixed case — leave it alone
    low = s.lower()
    out, cap = [], True
    for i, ch in enumerate(low):
        if cap and ch.isalpha():
            out.append(ch.upper()); cap = False
        else:
            out.append(ch)
        if ch in "?!" or (ch == "." and not (i + 1 < len(low) and low[i + 1] == ".")):
            # ellipses ("..", "...") and "…" do not start a new sentence
            nxt = low[i + 1: i + 2]
            if nxt in ("", " ", '"', "'"):
                cap = True
    res = "".join(out)
    for n in names:
        for part in n.split():
            if len(part) > 2:
                res = re.sub(rf"\b{re.escape(part.lower())}\b", part.capitalize(), res)
    return res


def main():
    src, dst = sys.argv[1], sys.argv[2]
    keep_case = "--keep-case" in sys.argv
    text = open(src, encoding="utf-8").read()
    blocks = blocks_from(text)

    # ---- title page: page 1 with no scene heading and title-page words
    title_page = None
    p1 = [b for b in blocks if b["page"] == 1]
    if p1 and not any(HEAD.match(b["text"]) for b in p1) and re.search(r"written by|screenplay by|story by|draft", " ".join(b["text"] for b in p1), re.I):
        raw = [l for b in p1 for l in b["lines"]]
        clean = lambda l: re.sub(r"\s+", " ", l).strip()
        center = [clean(l) for l in raw if len(l) - len(l.lstrip()) >= 5]
        contact = [clean(l) for l in raw if len(l) - len(l.lstrip()) < 5]
        if not center:
            center, contact = [clean(l) for l in raw], []
        tp = {"title": center[0], "center": center[1:], "contact": contact}
        title_page = tp
        blocks = [b for b in blocks if b["page"] != 1]

    # ---- first pass: classify
    els = []
    cue_names = set()
    for b in blocks:
        t = b["text"]
        m = HEAD.match(t) if re.match(r"^\s*(SCENE\s*[-:#]?\s*\d+[A-Z]?\W*\s*)?(INT|EXT|I\s*/\s*E)\b", t, re.I) else None
        if m:
            first = b["lines"][0]
            fm = HEAD.match(first)
            rest_first = fm.group("rest") if fm else m.group("rest")
            loc, time = split_loc_time([rest_first] + b["lines"][1:])
            heading = f"{norm_ie(m.group('ie'))} {loc}" + (f" - {time}" if time else "")
            els.append(dict(type="scene_heading", text=heading, number=m.group("num") or ""))
            continue
        sm = SCENE_ONLY.match(t)
        if sm and len(t) < 80:
            els.append(dict(type="scene_heading", text=sm.group("rest").upper().strip(), number=sm.group("num"),
                            flag="Scene line without INT./EXT. — check the heading."))
            continue
        tm = TRANS.match(t)
        if tm:
            tt = tm.group("t").upper()
            if tt in ("CUT", "DISSOLVE", "SMASH CUT", "MATCH CUT", "JUMP CUT"):
                tt += " TO"
            if tt in ("FADE OUT",):
                txt = "FADE OUT."
            elif tt == "FADE IN":
                txt = "FADE IN:"
            else:
                txt = tt + ":"
            els.append(dict(type="transition", text=txt))
            continue
        cm = INLINE_CUE.match(t)
        if cm and cm.group("name").strip() and cm.group("name").strip() == cm.group("name").strip().upper() and cm.group("rest").strip():
            name = re.sub(r"\s+", " ", cm.group("name")).strip()
            cue_names.add(name)
            el = dict(type="character", text=name)
            if cm.group("ext"):
                el["ext"] = cm.group("ext").upper().replace("CONTD", "CONT'D")
            els.append(el)
            els.append(dict(type="dialogue", text=cm.group("rest").strip()))
            continue
        # standard-format input: short all-caps line, deeply indented, then dialogue lines
        first = b["lines"][0].strip()
        if b["indent"] >= 15 and first.isupper() and len(first) <= 35 and not first.startswith("("):
            name = re.sub(r"\s*\((V\.?O\.?|O\.?S\.?|CONT'?D)\)\s*$", "", first, flags=re.I)
            ext = first[len(name):].strip()
            cue_names.add(name)
            el = dict(type="character", text=name)
            if ext:
                el["ext"] = ext.upper()
            els.append(el)
            rest = " ".join(l.strip() for l in b["lines"][1:]).strip()
            if rest:
                pm = re.match(r"^(\([^)]*\))\s*(.*)$", rest)
                if pm:
                    els.append(dict(type="parenthetical", text=pm.group(1)))
                    rest = pm.group(2)
                if rest:
                    els.append(dict(type="dialogue", text=rest))
            continue
        if t.startswith("(") and t.endswith(")"):
            els.append(dict(type="_paren", text=t))
            continue
        els.append(dict(type="action", text=t, _page=b["page"]))

    # ---- second pass: bracketed blocks -> parenthetical of next speaker, or action
    out = []
    i = 0
    while i < len(els):
        e = els[i]
        if e["type"] == "_paren":
            words = len(re.findall(r"\w+", e["text"]))
            nxt = els[i + 1] if i + 1 < len(els) else None
            if nxt and nxt["type"] == "character" and words <= 6:
                out.append(nxt)
                p = dict(type="parenthetical", text=e["text"],
                         flag="Moved from above the cue to under it (parenthetical of the next speaker) — confirm.")
                out.append(p)
                i += 2
                continue
            inner = e["text"][1:-1].strip()
            out.append(dict(type="action", text=inner, flag="Bracketed description turned into an action line — confirm."))
            i += 1
            continue
        out.append(e)
        i += 1

    # ---- third pass: merge action split by a page break / stray gap mid-sentence
    merged = []
    for e in out:
        if (merged and e["type"] == "action" and merged[-1]["type"] == "action"
                and not re.search(r"[.!?…\"')]$", merged[-1]["text"]) and e["text"][:1].islower()):
            merged[-1]["text"] += " " + e["text"]
            merged[-1]["flag"] = "Joined two pieces of one sentence (split by a page break or gap) — confirm."
            continue
        merged.append(e)

    # ---- casing: dialogue to sentence case; character names in action
    names = sorted(cue_names, key=len, reverse=True)
    seen = set()
    for e in merged:
        e.pop("_page", None)
        if e["type"] == "dialogue" and not keep_case:
            e["text"] = sentence_case(e["text"], names)
        if e["type"] == "action":
            t = e["text"]
            if t[:1].islower():
                t = t[0].upper() + t[1:]
            for n in names:
                pat = re.compile(rf"\b{re.escape(n)}\b", re.I)
                def rep(m, n=n):
                    if n not in seen:
                        seen.add(n)
                        return n.upper()          # first appearance in action: CAPS
                    return " ".join(w.capitalize() for w in n.split())
                t = pat.sub(rep, t)
            e["text"] = t
        if e["type"] == "parenthetical":
            for n in names:
                e["text"] = re.sub(rf"\b{re.escape(n)}\b", lambda m, n=n: " ".join(w.capitalize() for w in n.split()), e["text"], flags=re.I) if not e["text"].isupper() else e["text"]
        if e["type"] == "character":
            seen.add(e["text"])  # spoke before being introduced — don't caps later

    doc = {"title_page": title_page, "elements": merged, "notes": []}
    json.dump(doc, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    counts = {}
    for e in merged:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    flags = sum(1 for e in merged if e.get("flag"))
    print(f"draft: {len(merged)} elements {counts}; {flags} flagged for review; title page: {'yes' if title_page else 'no'}")


if __name__ == "__main__":
    main()
