#!/usr/bin/env python3
"""Cross-check 1 — was every page of the original actually read?

Usage: page_check.py <original file> <source.txt> [--report checks/pages.json] [--min-words 8]

For PDFs:
  - the PDF's page count must equal the number of pages in source.txt
  - each page's word count is listed; a page with fewer than --min-words words is "low text"
  - a low-text page that contains an image is treated as scanned: it is OCR'd (tesseract, English
    letters — fine for Tinglish) and the OCR text is put into source.txt in that page's place
  - pages that are still empty after OCR are reported as UNREAD — Claude must look at the page image
    (pdftoppm) and type its text into source.txt (or confirm the page is genuinely blank)
For DOCX/TXT/Fountain there are no fixed pages: it reports total words and paragraphs only.
Exit 1 if any page is UNREAD or the page counts don't match.
"""
import json, os, re, subprocess, sys, tempfile, pathlib

TOK = re.compile(r"[A-Za-z0-9ఀ-౿]+")


def words(t):
    return len(TOK.findall(t))


def pdf_pages(pdf):
    out = subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", out, re.M)
    return int(m.group(1)) if m else 0


def page_has_image(pdf, p):
    out = subprocess.run(["pdfimages", "-list", "-f", str(p), "-l", str(p), pdf], capture_output=True, text=True).stdout
    return len(out.strip().splitlines()) > 2


def ocr_page(pdf, p):
    d = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-f", str(p), "-l", str(p), pdf, f"{d}/pg"], check=True)
    img = sorted(pathlib.Path(d).glob("pg*.png"))[0]
    r = subprocess.run(["tesseract", str(img), "-", "--psm", "4", "-l", "eng"], capture_output=True, text=True)
    return r.stdout


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    orig, srcp = args[0], args[1]
    report = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    min_words = int(sys.argv[sys.argv.index("--min-words") + 1]) if "--min-words" in sys.argv else 8
    text = open(srcp, encoding="utf-8").read()
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]          # pdftotext ends with a trailing form feed
    rep = {"file": os.path.basename(orig), "kind": "pdf" if orig.lower().endswith(".pdf") else "text", "pages": []}
    ok = True

    if rep["kind"] != "pdf":
        rep["total_words"] = words(text)
        rep["paragraphs"] = len([b for b in re.split(r"\n\s*\n", text) if b.strip()])
        print(f"{rep['file']}: not a PDF — {rep['total_words']} words, {rep['paragraphs']} paragraphs (no fixed pages to check)")
    else:
        n = pdf_pages(orig)
        rep["pdf_pages"], rep["read_pages"] = n, len(pages)
        if n != len(pages):
            ok = False
            print(f"ERROR page count: PDF has {n} pages but {len(pages)} were read")
        changed = False
        for i, ptxt in enumerate(pages, start=1):
            w = words(ptxt)
            entry = {"page": i, "words": w, "status": "ok"}
            if w < min_words:
                if page_has_image(orig, i):
                    o = ocr_page(orig, i)
                    ow = words(o)
                    if ow >= min_words:
                        pages[i - 1] = o
                        changed = True
                        entry.update(words=ow, status="ocr", note="scanned page — text read with OCR; check it")
                    else:
                        entry.update(status="UNREAD", note="image page, OCR found no text — read the page image yourself")
                        ok = False
                elif w == 0:
                    entry.update(status="blank", note="no text and no image — looks genuinely blank")
                else:
                    entry.update(status="low", note=f"only {w} words — check the page image")
            rep["pages"].append(entry)
        if changed:
            open(srcp, "w", encoding="utf-8").write("\f".join(pages) + "\f")
        for e in rep["pages"]:
            flag = "" if e["status"] == "ok" else f"  ← {e['status'].upper()}: {e.get('note','')}"
            print(f"page {e['page']:>3}: {e['words']:>4} words{flag}")
        rep["total_words"] = sum(e["words"] for e in rep["pages"])
        print(f"PDF pages {n}, pages read {len(pages)}, total words {rep['total_words']}")

    rep["result"] = "PASS" if ok else "FAIL"
    if report:
        os.makedirs(os.path.dirname(report) or ".", exist_ok=True)
        json.dump(rep, open(report, "w"), indent=1)
    print(rep["result"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
