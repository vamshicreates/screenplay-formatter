#!/usr/bin/env python3
"""Cross-check 3 — did everything make it into the finished files?

Usage: check_output.py <script.json> <out.docx> [--mode en|te|full] [--report checks/output-<mode>.json]
       (the .pdf next to the .docx is checked too, if present)

.docx: re-opened and compared paragraph by paragraph with script.json — every element must appear,
       in order, with exactly its words (Telugu text in the Telugu modes). Only these extras are allowed:
       the scene number printed in both margins, and (CONT'D)/(V.O.)/(O.S.) after a character name.
.pdf:  must open and have pages; its letters (Telugu and English, spaces ignored) are counted and must
       match the .docx letter for letter, apart from page numbers. (PDF text extraction can reorder
       blocks and split Telugu words, so letters are compared as counts, not order.)
Exit 0 = PASS.
"""
import collections, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import toks

LETTER = re.compile(r"[A-Za-z0-9ఀ-౿]")


def expected_paragraphs(doc, mode):
    use_te = lambda e: (mode == "full" and e["type"] != "character") or (mode in ("te", "full") and e["type"] == "dialogue")
    exp = []
    tp = doc.get("title_page")
    if tp:
        full = mode == "full"
        exp.append(("title", (tp.get("title_te") if full else None) or tp.get("title", "")))
        for part in ("center", "contact"):
            tes = tp.get(part + "_te") or []
            for n, l in enumerate(tp.get(part, [])):
                exp.append((f"title page {part}", (tes[n] if full and n < len(tes) and tes[n] else l)))
    for i, e in enumerate(doc["elements"]):
        txt = e.get("te") if use_te(e) else e["text"]
        exp.append((f"#{i} {e['type']}", txt or e["text"], e))
    return exp


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "en"
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    doc = json.load(open(args[0], encoding="utf-8"))
    docx_path = args[1]
    import docx
    paras = [p.text for p in docx.Document(docx_path).paragraphs if p.text.strip()]
    exp = expected_paragraphs(doc, mode)
    problems = []

    EXT = r"\((?:CONT'?D|V\.?O\.?|O\.?S\.?|O\.?C\.?)\)"

    def norm_got(t):
        m = re.match(r"^(\S+)\t(.*)\t\1$", t, re.S)          # scene number in both margins
        if m:
            t = m.group(2)
        return tuple(toks(re.sub(EXT, " ", t, flags=re.I)))

    def norm_want(item):
        return tuple(toks(re.sub(EXT, " ", item[1], flags=re.I)))

    G = [norm_got(t) for t in paras]
    W = [norm_want(it) for it in exp]
    import difflib
    sm = difflib.SequenceMatcher(a=W, b=G, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        for k in range(a1, a2):
            hit = paras[b1 + (k - a1)] if op == "replace" and b1 + (k - a1) < b2 else None
            if hit is None:
                problems.append(f"MISSING {exp[k][0]}: “{exp[k][1][:70]}”")
            else:
                problems.append(f"CHANGED {exp[k][0]}: expected “{exp[k][1][:70]}” — found “{hit[:70]}”")
        if op in ("insert", "replace") and (b2 - b1) > (a2 - a1):
            for k in range(b1 + (a2 - a1), b2):
                problems.append(f"EXTRA paragraph in .docx: “{paras[k][:70]}”")
    # Telugu present where it should be
    if mode in ("te", "full"):
        for k, item in enumerate(exp):
            e = item[2] if len(item) > 2 else None
            if e is None or not (e["type"] == "dialogue" or (mode == "full" and e["type"] != "character")):
                continue
            if not re.search(r"[\u0C00-\u0C7F]", item[1]):
                problems.append(f"{item[0]}: should be in Telugu letters but has no Telugu text")
    docx_ok = not problems

    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    pdf_info = {}
    if os.path.exists(pdf_path):
        info = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout
        m = re.search(r"^Pages:\s+(\d+)", info, re.M)
        pdf_info["pages"] = int(m.group(1)) if m else 0
        if not pdf_info["pages"]:
            problems.append("PDF has no pages or won't open")
        else:
            ptxt = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True, text=True).stdout
            ptxt = re.sub(r"(?m)^\s*\d{1,3}\.\s*$", "", ptxt)          # page numbers "2."
            want = collections.Counter(LETTER.findall("".join(paras)))
            got = collections.Counter(LETTER.findall(ptxt))
            missing = want - got
            extra = got - want
            if missing or extra:
                problems.append(f"PDF letters differ from the .docx — missing {sum(missing.values())} "
                                f"({''.join(sorted(missing.elements()))[:40]}), extra {sum(extra.values())} "
                                f"({''.join(sorted(extra.elements()))[:40]})")
    else:
        pdf_info["note"] = "no PDF found next to the .docx"

    print(f".docx: {len(paras)} paragraphs vs {len(exp)} expected — {'✓' if docx_ok else '✗'}")
    if pdf_info.get("pages"):
        print(f".pdf:  {pdf_info['pages']} pages — {'✓' if not [p for p in problems if p.startswith('PDF')] else '✗'}")
    result = "FAIL" if problems else "PASS"
    for p in problems:
        print("  " + p)
    print(f"{result} — finished files contain everything" if not problems else f"{result} — {len(problems)} problem(s)")
    if report:
        os.makedirs(os.path.dirname(report) or ".", exist_ok=True)
        json.dump({"result": result, "mode": mode, "docx": os.path.basename(docx_path), "paragraphs": len(paras),
                   "expected": len(exp), "pdf": pdf_info, "problems": problems},
                  open(report, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
