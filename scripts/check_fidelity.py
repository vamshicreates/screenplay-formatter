#!/usr/bin/env python3
"""Word-level fidelity check: does script.json contain exactly the words of source.txt?

Usage: check_fidelity.py <source.txt> <script.json>

Compares every word (case-insensitive, punctuation ignored) in reading order.
Allowed format-only differences:
  - dropped:  "scene" before a scene number in a heading (number moves to the margins)
  - added:    "to" in transitions ("CUT" -> "CUT TO:")
  - speaker cues are compared separately (their position relative to a moved
    parenthetical may change, but the sequence of speakers must be identical).
Exit code 0 = PASS, 1 = differences found (listed with context).
"""
import json, re, sys, difflib

PAGE_NUM = re.compile(r"^\s*\(?\d{1,3}\)?\s*\.?\s*$", re.M)
TOK = re.compile(r"[a-z0-9]+")


def toks(s):
    return TOK.findall(s.lower().replace("’", "'").replace("'", ""))


def main():
    src = open(sys.argv[1], encoding="utf-8").read().replace("\f", "\n")
    doc = json.load(open(sys.argv[2], encoding="utf-8"))
    els = doc["elements"]
    cues = []
    for e in els:
        if e["type"] == "character":
            cues.append(e["text"].upper())
    names = sorted(set(cues), key=len, reverse=True)

    # --- source: drop page numbers, pull out speaker cues
    src = PAGE_NUM.sub("", src)
    src_cues = []
    if names:
        alt = "|".join(re.escape(n) for n in names)
        cue_re = re.compile(rf"(?m)^[ \t]*({alt})[ \t]*(\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D)\))?[ \t]*(:|$)")
        def grab(m):
            src_cues.append(m.group(1).upper())
            return " "
        src = cue_re.sub(grab, src)
    st = toks(src)

    # --- output tokens (cues excluded, scene numbers included)
    ot = []
    tp = doc.get("title_page") or {}
    if tp:
        for k in ("title",):
            ot += toks(tp.get(k, ""))
        for l in tp.get("center", []) + tp.get("contact", []):
            ot += toks(l)
    for e in els:
        if e["type"] == "character":
            continue
        if e["type"] == "scene_heading" and e.get("number"):
            ot += toks(e["number"])
        ot += toks(e["text"])

    problems = []
    sm = difflib.SequenceMatcher(a=st, b=ot, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        gone, added = st[a1:a2], ot[b1:b2]
        if op == "delete" and set(gone) <= {"scene"}:
            continue
        if op == "insert" and set(added) <= {"to"}:
            continue
        if op == "replace" and set(gone) <= {"scene"} and set(added) <= {"to"}:
            continue
        ctx = " ".join(st[max(0, a1 - 6):a1])
        problems.append(f"[{op}] after “…{ctx}”:  source={' '.join(gone) or '∅'}  →  output={' '.join(added) or '∅'}")

    if src_cues != cues:
        sm2 = difflib.SequenceMatcher(a=src_cues, b=cues, autojunk=False)
        for op, a1, a2, b1, b2 in sm2.get_opcodes():
            if op != "equal":
                problems.append(f"[speaker {op}] source cues {src_cues[a1:a2]} → output cues {cues[b1:b2]} (at cue #{a1+1})")

    print(f"source words: {len(st)}  output words: {len(ot)}  speakers: {len(src_cues)} vs {len(cues)}")
    if problems:
        print(f"FAIL — {len(problems)} difference(s):")
        for p in problems:
            print("  " + p)
        sys.exit(1)
    print("PASS — every word of the original is present, in order, and nothing was added.")


if __name__ == "__main__":
    main()
