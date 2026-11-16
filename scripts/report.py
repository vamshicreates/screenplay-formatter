#!/usr/bin/env python3
"""Build the human-readable check report from the checks/ folder.

Usage: report.py <checks dir> <out.txt> [--title "sample script"]

Reads (whichever exist): pages.json, fidelity.json, telugu-te.json, telugu-full.json,
output-en.json, output-te.json, output-full.json, review.json
review.json = {"reviewers": N, "packets": [...], "findings": [{..., "action": "fixed"|"rejected", "note": "..."}]}
"""
import json, os, sys, datetime


def load(d, name):
    p = os.path.join(d, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def mark(r):
    return "✓ PASS" if r == "PASS" else ("✗ FAIL" if r == "FAIL" else "–")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    d, out = args[0], args[1]
    title = sys.argv[sys.argv.index("--title") + 1] if "--title" in sys.argv else ""
    pages, fid = load(d, "pages.json"), load(d, "fidelity.json")
    L = []
    L += [f"CHECK REPORT — {title}".strip(" —"), f"Generated {datetime.datetime.now():%d %b %Y, %H:%M}", "=" * 64, ""]

    summary = []
    if pages: summary.append(("1. Every page read", pages["result"]))
    if fid: summary.append(("2. Every word kept (page by page)", fid["result"]))
    for m, lab in (("te", "Telugu V1 lines"), ("full", "Telugu V2/V3 lines")):
        t = load(d, f"telugu-{m}.json")
        if t: summary.append((f"3. {lab} complete & clean", t["result"]))
    for m, lab in (("en", "standard"), ("te", "Telugu V1"), ("full", "Telugu V2"), ("v3", "Telugu V3")):
        o = load(d, f"output-{m}.json")
        if o: summary.append((f"4. Finished files complete ({lab})", o["result"]))
    rev = load(d, "review.json")
    if rev:
        open_items = [f for f in rev["findings"] if f.get("action") not in ("fixed", "rejected")]
        summary.append(("5. Independent review", "PASS" if not open_items else "FAIL"))
    L.append("SUMMARY")
    for lab, r in summary:
        L.append(f"  {lab:<44} {mark(r)}")
    overall = all(r == "PASS" for _, r in summary)
    L += ["", f"  OVERALL: {'ALL CHECKS PASSED' if overall else 'ATTENTION NEEDED — see below'}", ""]

    if pages and fid:
        L += ["PAGE BY PAGE", f"  {'page':>4}  {'script words':>12}  {'found in output':>15}  status"]
        fp = {p["page"]: p for p in fid["pages"]}
        for p in pages.get("pages", []):
            f = fp.get(p["page"], {"words": 0, "matched": 0, "ok": p["words"] == 0})
            st = "✓" if f.get("ok", False) and p["status"] in ("ok", "ocr", "blank") else "✗"
            note = {"ocr": "  (scanned — read with OCR)", "blank": "  (blank page)", "low": "  (very little text)",
                    "UNREAD": "  (COULD NOT BE READ)"}.get(p["status"], "")
            L.append(f"  {p['page']:>4}  {f['words']:>12}  {f['matched']:>15}  {st}{note}")
        L += [f"  PDF pages: {pages.get('pdf_pages','–')}   pages read: {pages.get('read_pages','–')}   "
              f"words compared: {fid['source_words']}   speeches: {fid['speakers'][0]}", ""]
        L.append("  (page numbers aren't counted; character names are checked separately as the order of speeches)")
        L.append("")
    elif fid:
        L += [f"WORDS: {fid['source_words']} compared, speeches {fid['speakers'][0]}", ""]
    if fid and fid["differences"]:
        L += ["WORD DIFFERENCES"] + [f"  {x}" for x in fid["differences"]] + [""]

    for m, lab in (("te", "TELUGU V1 (dialogue)"), ("full", "TELUGU V2/V3 (full)")):
        t = load(d, f"telugu-{m}.json")
        if t:
            L.append(f"{lab}: {t['lines']} lines checked — {mark(t['result'])}")
            for e in t["errors"]:
                L.append(f"  ERROR  {e}")
            for r in dict.fromkeys(t["review"]):
                L.append(f"  flag checked, OK: {r.split(' — sounds')[0]}")
            L.append("")
    for m, lab in (("en", "standard"), ("te", "Telugu V1"), ("full", "Telugu V2"), ("v3", "Telugu V3")):
        o = load(d, f"output-{m}.json")
        if o:
            pg = o.get("pdf", {}).get("pages", "–")
            L.append(f"FINISHED FILES ({lab}): {o['docx']} — {o['paragraphs']}/{o['expected']} paragraphs, PDF {pg} pages — {mark(o['result'])}")
            for p in o["problems"]:
                L.append(f"  {p}")
    L.append("")

    if rev:
        L.append(f"INDEPENDENT REVIEW: {rev.get('reviewers', len(rev.get('packets', [])))} reviewer(s), "
                 f"{len(rev['findings'])} finding(s)")
        for f in rev["findings"]:
            where = f"#{f['element']}" if f.get("element") is not None else f"page {f.get('page','?')}"
            L.append(f"  [{f.get('action','OPEN').upper()}] {where} {f.get('kind','')}: {f.get('problem','')}"
                     + (f" → {f.get('note')}" if f.get("note") else ""))
        if not rev["findings"]:
            L.append("  No problems found.")
        L.append("")

    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
