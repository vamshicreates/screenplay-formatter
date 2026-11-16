#!/usr/bin/env python3
"""Extract a script file to layout-preserving plain text (source.txt).

Usage: extract_text.py <input.(pdf|docx|txt|fountain|md)> <out.txt>

Pages are separated by form feeds (\f). For .docx, paragraph left indents are
turned into leading spaces (1 space per 0.1") so the draft parser can still
use indentation as a hint.
"""
import subprocess, sys, pathlib


def from_pdf(p):
    r = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, check=True)
    return r.stdout


def from_docx(p):
    import docx
    d = docx.Document(str(p))
    out = []
    for para in d.paragraphs:
        ind = para.paragraph_format.left_indent
        spaces = int(round(ind.inches * 10)) if ind else 0
        if para.alignment is not None and int(para.alignment) == 1:  # centered
            spaces = max(spaces, 20)
        txt = para.text
        if any(r.element.xpath('.//w:br[@w:type="page"]') for r in para.runs):
            out.append("\f")
        out.append((" " * spaces + txt) if txt.strip() else "")
    return "\n".join(out)


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    ext = src.suffix.lower()
    if ext == ".pdf":
        text = from_pdf(src)
    elif ext == ".docx":
        text = from_docx(src)
    else:
        text = src.read_text(encoding="utf-8", errors="replace")
    dst.write_text(text, encoding="utf-8")
    pages = text.count("\f") + 1
    words = len(text.split())
    print(f"extracted {dst} — {pages} page(s), {words} words")
    if words < 20 and ext == ".pdf":
        print("WARNING: almost no text — the PDF may be scanned. OCR it first (pdf skill) or ask for the source file.")


if __name__ == "__main__":
    main()
