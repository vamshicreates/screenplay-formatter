#!/usr/bin/env python3
"""Cross-check 3 — did everything make it into the finished files?

Usage: check_output.py <script.json> <out.docx> [--mode en|te|full|v3] [--report checks/output-<mode>.json]
       (the .pdf next to the .docx is checked too, if present)

.docx: re-opened and compared paragraph by paragraph with script.json — every element must appear,
       in order, with exactly its words (Telugu text in the Telugu modes). Only these extras are allowed:
       the scene number printed in both margins, and (CONT'D)/(V.O.)/(O.S.) after a character name.
V3:    the two-column layout is read row by row from the .docx tables (left | name : | dialogue) and
       compared with common.v3_rows(); every script line must land in exactly one row, and every
       character name must be in Telugu letters.
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


def docx_units(path):
    """Body in reading order: paragraph text, or a table row as 'left | name | dialogue' (joined by \x1f)."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    d = docx.Document(path)
    units = []
    for child in d.element.body.iterchildren():
        if child.tag.endswith("}p"):
            t = Paragraph(child, d).text
            if t.strip():
                units.append(t)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, d).rows:
                units.append("\x1f".join("\n".join(p.text for p in c.paragraphs) for c in row.cells))
    return units


def check_v3(doc, docx_path):
    from common import v3_layout
    problems = []
    rows = v3_layout(doc)
    # every element in exactly one unit
    seen = {}
    for u in rows:
        for i in u["idx"]:
            seen[i] = seen.get(i, 0) + 1
    for i, e in enumerate(doc["elements"]):
        if seen.get(i, 0) != 1:
            problems.append(f"#{i} {e['type']} appears {seen.get(i, 0)} times in the V3 layout (must be once): “{e['text'][:50]}”")
    names = doc.get("names_te", {})
    for n in sorted({e["text"] for e in doc["elements"] if e["type"] == "character"}):
        if not re.search(r"[\u0C00-\u0C7F]", names.get(n, "")) or re.search(r"[A-Za-z]", names.get(n, "")):
            problems.append(f"character name {n}: needs Telugu letters in names_te (has “{names.get(n, '')}”)")
    exp = []
    tp = doc.get("title_page")
    if tp:
        exp.append(tp.get("title_te") or tp.get("title", ""))
        for part in ("center", "contact"):
            tes = tp.get(part + "_te") or []
            exp += [(tes[n] if n < len(tes) and tes[n] else l) for n, l in enumerate(tp.get(part, []))]
    for u in rows:
        if u["kind"] == "heading":
            exp.append("\t".join(u["cols"]))
        elif u["kind"] == "transition":
            exp.append(u["text"])
        else:
            dl = "\n".join(x for x in (u["dlg"], u.get("trans", "")) if x)
            exp.append("\x1f".join([u["left"], u["name"], dl]))
    got = docx_units(docx_path)
    norm = lambda t: tuple(tuple(toks(c)) for c in t.split("\x1f"))
    import difflib
    sm = difflib.SequenceMatcher(a=[norm(x) for x in exp], b=[norm(x) for x in got], autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        for k in range(a1, a2):
            alt = got[b1 + (k - a1)] if op == "replace" and b1 + (k - a1) < b2 else None
            show = exp[k].replace("\x1f", " | ")[:80]
            problems.append(f"{'CHANGED' if alt else 'MISSING'} row: “{show}”" + (f" — found “{alt.replace(chr(31), ' | ')[:80]}”" if alt else ""))
        if op in ("insert", "replace") and (b2 - b1) > (a2 - a1):
            for k in range(b1 + (a2 - a1), b2):
                problems.append(f"EXTRA row in .docx: “{got[k].replace(chr(31), ' | ')[:80]}”")
    for u in rows:
        if u["kind"] == "row":
            for part in (u["left"], u["dlg"]):
                if part and not re.search(r"[\u0C00-\u0C7F]", part):
                    problems.append(f"row {u['idx']}: text not in Telugu letters: “{part[:50]}”")
    return got, exp, problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "en"
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    doc = json.load(open(args[0], encoding="utf-8"))
    docx_path = args[1]
    import docx
    problems = []
    if mode == "v3":
        paras, exp, problems = check_v3(doc, docx_path)
    else:
        paras = [p.text for p in docx.Document(docx_path).paragraphs if p.text.strip()]
        exp = expected_paragraphs(doc, mode)

    EXT = r"\((?:CONT'?D|V\.?O\.?|O\.?S\.?|O\.?C\.?)\)"
    if mode == "v3":
        G = W = []

    def norm_got(t):
        m = re.match(r"^(\S+)\t(.*)\t\1$", t, re.S)          # scene number in both margins
        if m:
            t = m.group(2)
        return tuple(toks(re.sub(EXT, " ", t, flags=re.I)))

    def norm_want(item):
        return tuple(toks(re.sub(EXT, " ", item[1], flags=re.I)))

    G = [norm_got(t) for t in paras] if mode != "v3" else []
    W = [norm_want(it) for it in exp] if mode != "v3" else []
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
            pages_ = []
            offset = 1 if doc.get("title_page") else 0
            for pk, pg in enumerate(ptxt.split("\f"), start=1):        # drop the page number printed at the top
                sp_ = pk - offset                                          # script page number
                has_hdr = sp_ >= 1 and (mode == "v3" or sp_ >= 2)          # en/te/full: none on script page 1
                ls = pg.split("\n")
                for k, l in enumerate(ls):
                    if l.strip():
                        if has_hdr and l.strip() in (str(sp_), f"{sp_}."):
                            ls[k] = ""
                        break
                pages_.append("\n".join(ls))
            ptxt = "\f".join(pages_)
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
