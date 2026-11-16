#!/usr/bin/env python3
"""Cross-check 2 — word-for-word fidelity, page by page.

Usage: check_fidelity.py <source.txt> <script.json> [--report checks/fidelity.json]

Compares every word of the original (case and punctuation ignored) with script.json, in reading order.
Allowed format-only differences: "scene" dropped before a scene number, "to" added in "CUT TO:".
Speaker cues are compared as a separate sequence (a moved parenthetical may change their position).
Prints a per-page table (every original page must be ✓) and lists each difference with its page.
With --report, also writes each element's source page (used by review_packets.py).
Exit 0 = PASS, 1 = differences found.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import source_tokens, output_tokens, align
import difflib


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    src_text = open(args[0], encoding="utf-8").read()
    doc = json.load(open(args[1], encoding="utf-8"))
    cues = [e["text"].upper() for e in doc["elements"] if e["type"] == "character"]

    st, sp, src_cues, npages = source_tokens(src_text, cues)
    ot, owner = output_tokens(doc)
    problems, src_ok, out_map = align(st, ot)

    # per-page coverage
    pages = {}
    for k, p in enumerate(sp):
        d = pages.setdefault(p, {"page": p, "words": 0, "matched": 0, "issues": 0})
        d["words"] += 1
        d["matched"] += 1 if src_ok[k] else 0
    lines = []
    for op, a1, a2, b1, b2 in problems:
        gone, added = st[a1:a2], ot[b1:b2]
        p = sp[min(a1, len(sp) - 1)] if sp else 1
        pages.setdefault(p, {"page": p, "words": 0, "matched": 0, "issues": 0})["issues"] += 1
        ctx = " ".join(st[max(0, a1 - 6):a1])
        lines.append(f"page {p}: [{op}] after “…{ctx}”:  original={' '.join(gone) or '∅'}  →  output={' '.join(added) or '∅'}")

    src_cue_names = [c for c, _ in src_cues]
    if src_cue_names != cues:
        sm2 = difflib.SequenceMatcher(a=src_cue_names, b=cues, autojunk=False)
        for op, a1, a2, b1, b2 in sm2.get_opcodes():
            if op != "equal":
                p = src_cues[min(a1, len(src_cues) - 1)][1] if src_cues else 1
                pages.setdefault(p, {"page": p, "words": 0, "matched": 0, "issues": 0})["issues"] += 1
                lines.append(f"page {p}: [speaker {op}] original {src_cue_names[a1:a2]} → output {cues[b1:b2]}")

    print(f"{'page':>5} {'words':>6} {'matched':>8}  status")
    for p in sorted(pages):
        d = pages[p]
        d["ok"] = d["issues"] == 0 and d["matched"] == d["words"]
        print(f"{p:>5} {d['words']:>6} {d['matched']:>8}  {'✓' if d['ok'] else '✗ ' + str(d['issues']) + ' issue(s)'}")
    print(f"total: original {len(st)} words, output {len(ot)} words; speakers {len(src_cue_names)} vs {len(cues)}")

    result = "FAIL" if lines else "PASS"
    if lines:
        print(f"FAIL — {len(lines)} difference(s):")
        for l in lines:
            print("  " + l)
    else:
        print("PASS — every word of every page is present, in order, and nothing was added.")

    if report:
        from common import element_pages
        os.makedirs(os.path.dirname(report) or ".", exist_ok=True)
        json.dump({"result": result, "source_words": len(st), "output_words": len(ot),
                   "speakers": [len(src_cue_names), len(cues)],
                   "pages": [pages[p] for p in sorted(pages)], "differences": lines,
                   "element_pages": element_pages(doc, sp, owner, out_map)},
                  open(report, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if lines else 0)


if __name__ == "__main__":
    main()
