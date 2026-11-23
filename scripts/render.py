#!/usr/bin/env python3
"""Render script.json to an industry-standard screenplay .docx (and .pdf).

Usage: render.py <script.json> <out.docx> [--telugu | --telugu-full | --v3 | --v4] [--pdf] [--no-scene-numbers]

Format (US spec screenplay):
  Letter 8.5x11, Courier New 12 pt, 6 lines per inch (exactly 12 pt line pitch)
  Margins: left 1.5", right 1", top 1", bottom 1"; page numbers top-right "2." (none on page 1)
  Scene heading: flush left, CAPS, scene number in both margins, blank line(s) before
  Action: flush left, full width (6.0")
  Character cue: 3.7" from page edge, CAPS, (CONT'D) added automatically
  Parenthetical: 3.1" from edge, ~2.4" wide
  Dialogue: 2.5" from edge, 3.5" wide
  Transition: flush right, CAPS
Cue+parenthetical+dialogue never split across pages; headings never end a page.
--telugu:      V1 — dialogue uses each element's "te" text, Telugu letters set in Noto Sans Telugu.
--telugu-full: V2 — every element (title page, headings, action, parentheticals, transitions,
               dialogue) uses its "te" text; only character names stay English CAPS.
--v3:          V3 — Telugu two-column layout used by Telugu film crews: English scene-heading bar
               ("4.INT   LOCATION   -TIME"), then action in Telugu on the left and "name :" + dialogue in
               Telugu on the right, an action that leads into a speech sitting beside it (see common.v3_rows).
               Needs "te" on every non-character element and doc["names_te"] for the character names.
--v4:          V4 — the same two-column crew layout with ALL text in English letters: the writer's own
               words from script.json, character names as written ("SUGUNA :"). No Telugu step needed.
"""
import json, re, sys, subprocess, pathlib
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

FONT = "Courier New"
TE_FONT = "Noto Sans Telugu"
TE_RE = re.compile(r"([ఀ-౿‌‍]+(?:[ ‌‍]+[ఀ-౿‌‍]+)*)")


def set_run_font(run, name, size=12, cs=False):
    run.font.name = name
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.insert(0, rf)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)
    if cs:
        rf.set(qn("w:hint"), "cs")
        szcs = OxmlElement("w:szCs"); szcs.set(qn("w:val"), str(size * 2)); rpr.append(szcs)
        lang = OxmlElement("w:lang"); lang.set(qn("w:bidi"), "te-IN"); rpr.append(lang)


def para(doc, text="", *, left=0.0, right=0.0, first=0.0, before=0, align=None,
         keep_next=False, keep_together=False, line=12, telugu=False):
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.left_indent, f.right_indent, f.first_line_indent = Inches(left), Inches(right), Inches(first)
    f.space_before, f.space_after = Pt(before), Pt(0)
    f.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    f.line_spacing = Pt(line)
    f.keep_with_next, f.keep_together, f.widow_control = keep_next, keep_together, True
    if align is not None:
        p.alignment = align
    if text:
        if telugu:
            for chunk in TE_RE.split(text):
                if not chunk:
                    continue
                r = p.add_run(chunk)
                if TE_RE.fullmatch(chunk):
                    set_run_font(r, TE_FONT, 13, cs=True)
                else:
                    set_run_font(r, FONT)
        else:
            set_run_font(p.add_run(text), FONT)
    return p


def add_page_number_header(section):
    section.different_first_page_header_footer = True
    hp = section.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.paragraph_format.right_indent = Inches(0)
    r = hp.add_run()
    set_run_font(r, FONT)
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tag); r._element.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._element.append(it)
    set_run_font(hp.add_run("."), FONT)
    # restart numbering at 1 for the script section
    sectPr = section._sectPr
    pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1"); sectPr.append(pg)


def setup_section(s):
    s.page_width, s.page_height = Inches(8.5), Inches(11)
    s.left_margin, s.right_margin = Inches(1.5), Inches(1.0)
    s.top_margin, s.bottom_margin = Inches(1.0), Inches(1.0)
    s.header_distance, s.footer_distance = Inches(0.5), Inches(0.5)


def title_page(doc, tp, full=False):
    """Title ~1/3 down, credit lines centred under it, contact block bottom-left.
    Spacing is tracked in points so taller Telugu lines still fit on one page."""
    def pick(en, te):
        return (te or en) if full else en
    lh = 18 if full else 12
    usable = 9 * 72 - 6                      # 9" of text area, small safety margin
    para(doc, pick(tp.get("title", "").upper(), tp.get("title_te")), align=WD_ALIGN_PARAGRAPH.CENTER,
         before=240, line=lh, telugu=full)
    used = 240 + lh
    centre = tp.get("center", [])
    cte = tp.get("center_te") or [None] * len(centre)
    for i, l in enumerate(centre):
        gap = 4 if (i > 0 and re.match(r"(based on|from|adapted)", l, re.I)) else (1 if i else 2)
        para(doc, pick(l, cte[i]), align=WD_ALIGN_PARAGRAPH.CENTER, before=12 * gap, line=lh, telugu=full)
        used += 12 * gap + lh
    contact = tp.get("contact", [])
    kte = tp.get("contact_te") or [None] * len(contact)
    if contact:
        gap = max(24, usable - used - lh * len(contact))
        for i, l in enumerate(contact):
            para(doc, pick(l, kte[i]), before=gap if i == 0 else 0, line=lh, telugu=full)


def render(doc_json, out, telugu=False, scene_numbers=True, full=False):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    setup_section(doc.sections[0])

    tp = doc_json.get("title_page")
    if tp:
        title_page(doc, tp, full)
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        setup_section(sec)
        sec.header.is_linked_to_previous = False
        sec.first_page_header.is_linked_to_previous = False
        add_page_number_header(sec)
    else:
        add_page_number_header(doc.sections[0])

    els = doc_json["elements"]
    first = True
    last_speaker, speech_seen_in_scene = None, False
    missing_te = []
    def tx(e):
        """Text to print for a non-character element in full-Telugu mode."""
        te = e.get("te")
        if not te:
            missing_te.append(els.index(e)); return e["text"]
        return te

    for i, e in enumerate(els):
        t = e["type"]
        nxt = els[i + 1]["type"] if i + 1 < len(els) else None
        if full and t in ("scene_heading", "action", "parenthetical", "transition"):
            txt = tx(e)
            if t == "scene_heading":
                last_speaker = None
                num = e.get("number", "") if scene_numbers else ""
                if num:
                    p = para(doc, f"{num}\t{txt}\t{num}", left=0, first=-0.75, right=-0.75,
                             before=0 if first else 24, keep_next=True, line=18, telugu=True)
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(0))
                    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.75), WD_TAB_ALIGNMENT.RIGHT)
                else:
                    para(doc, txt, before=0 if first else 24, keep_next=True, line=18, telugu=True)
            elif t == "action":
                para(doc, txt, before=0 if first else 12, line=18, telugu=True)
            elif t == "parenthetical":
                if not txt.strip().startswith("("):
                    txt = "(" + txt.strip() + ")"
                para(doc, txt, left=1.7, first=-0.1, right=1.9, keep_next=True, keep_together=True, line=18, telugu=True)
            else:
                if doc.paragraphs:
                    doc.paragraphs[-1].paragraph_format.keep_with_next = True
                para(doc, txt, align=WD_ALIGN_PARAGRAPH.RIGHT, before=12, line=18, telugu=True)
                last_speaker = None
            first = False
            continue
        if t == "scene_heading":
            last_speaker = None
            num = e.get("number", "") if scene_numbers else ""
            text = e["text"].upper()
            if num:
                p = para(doc, f"{num}\t{text}\t{num}", left=0, first=-0.75, right=-0.75,
                         before=0 if first else 24, keep_next=True)
                p.paragraph_format.tab_stops.add_tab_stop(Inches(0))
                p.paragraph_format.tab_stops.add_tab_stop(Inches(6.75), WD_TAB_ALIGNMENT.RIGHT)
            else:
                para(doc, text, before=0 if first else 24, keep_next=True)
        elif t == "action":
            para(doc, e["text"], before=0 if first else 12, keep_next=(nxt == "character" and False))
        elif t == "character":
            name = e["text"].upper()
            ext = e.get("ext", "")
            if name == last_speaker and "CONT" not in ext and not e.get("no_contd"):
                ext = (ext + " " if ext else "") + "(CONT'D)"
            para(doc, f"{name} {ext}".strip(), left=2.2, before=0 if first else 12, keep_next=True, keep_together=True)
            last_speaker = name
        elif t == "parenthetical":
            txt = e["text"].strip()
            if not txt.startswith("("):
                txt = "(" + txt + ")"
            para(doc, txt, left=1.7, first=-0.1, right=1.9, keep_next=True, keep_together=True)
        elif t == "dialogue":
            if telugu or full:
                te = e.get("te")
                if not te:
                    missing_te.append(i); te = e["text"]
                para(doc, te, left=1.0, right=1.5, keep_together=True, line=18, telugu=True)
            else:
                para(doc, e["text"], left=1.0, right=1.5, keep_together=True)
        elif t == "transition":
            if doc.paragraphs:                                   # keep CUT TO: with the line before it
                doc.paragraphs[-1].paragraph_format.keep_with_next = True
            para(doc, e["text"].upper(), align=WD_ALIGN_PARAGRAPH.RIGHT, before=12, keep_next=False)
            last_speaker = None
        else:
            para(doc, e.get("text", ""), before=12)
        first = False

    doc.save(out)
    if missing_te:
        print(f"WARNING: {len(missing_te)} dialogue element(s) had no Telugu text (indices {missing_te[:10]}…) — English kept.")
    print(f"wrote {out}")


def find_soffice():
    """LibreOffice's command: on PATH (Linux), or inside the app bundle (macOS) / Program Files (Windows)."""
    import shutil, os
    for c in ("soffice", "libreoffice"):
        if shutil.which(c):
            return shutil.which(c)
    for c in ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
              r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if os.path.exists(c):
            return c
    sys.exit("LibreOffice not found — install it (macOS: brew install --cask libreoffice) to make the PDF.")


# ------------------------------------------------------------------ V3: Telugu two-column layout
V3_LATIN = "Arial"


def v3_text(p, text, size_te=12, size_lat=11, bold=False):
    for chunk in TE_RE.split(text):
        if not chunk:
            continue
        r = p.add_run(chunk)
        if TE_RE.fullmatch(chunk):
            set_run_font(r, TE_FONT, size_te, cs=True)
        else:
            set_run_font(r, V3_LATIN, size_lat)
        r.bold = bold


def v3_para_fmt(p, align=None, before=0, after=4, line=17, keep_next=False):
    f = p.paragraph_format
    f.space_before, f.space_after = Pt(before), Pt(after)
    f.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    f.line_spacing = Pt(line)
    f.keep_with_next = keep_next
    if align is not None:
        p.alignment = align


def v3_cell(cell, text, width, align=None):
    cell.width = Inches(width)
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = tcPr.find(qn("w:tcW"))
    if tcW is None:
        tcW = OxmlElement("w:tcW"); tcPr.append(tcW)
    tcW.set(qn("w:w"), str(int(width * 1440))); tcW.set(qn("w:type"), "dxa")
    lines = text.split("\n") if text else [""]
    first = cell.paragraphs[0]
    for k, line in enumerate(lines):
        p = first if k == 0 else cell.add_paragraph()
        v3_para_fmt(p, align=align, after=2 if k < len(lines) - 1 else 6)
        if line:
            v3_text(p, line)


def render_v3(doc_json, out, latin=False):
    import sys as _s, os as _o
    _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
    from common import v3_layout
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = V3_LATIN, Pt(11)
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin, sec.right_margin = Inches(0.8), Inches(0.6)
    sec.top_margin, sec.bottom_margin = Inches(0.9), Inches(0.8)
    sec.header_distance = Inches(0.4)
    W = 8.5 - 0.8 - 0.6                       # 7.1" text width
    COLS = (2.95, 1.3, W - 2.95 - 1.3)        # action | "name :" | dialogue

    tp = doc_json.get("title_page")
    if tp:
        def pick(en, tt): return en if latin else (tt or en)
        p = doc.add_paragraph(); v3_para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, before=230, line=22)
        v3_text(p, pick(tp.get("title", "").upper() if latin else tp.get("title", ""), tp.get("title_te")), 16, 15, bold=True)
        cte = tp.get("center_te") or []
        for n, l in enumerate(tp.get("center", [])):
            p = doc.add_paragraph(); v3_para_fmt(p, align=WD_ALIGN_PARAGRAPH.CENTER, before=18)
            v3_text(p, pick(l, cte[n] if n < len(cte) else None))
        kte = tp.get("contact_te") or []
        for n, l in enumerate(tp.get("contact", [])):
            p = doc.add_paragraph(); v3_para_fmt(p, before=200 if n == 0 else 0)
            v3_text(p, pick(l, kte[n] if n < len(kte) else None))
        sec = doc.add_section(WD_SECTION.NEW_PAGE)
        sec.left_margin, sec.right_margin = Inches(0.8), Inches(0.6)
        sec.top_margin, sec.bottom_margin = Inches(0.9), Inches(0.8)
        sec.header.is_linked_to_previous = False
    # page number top right (plain "6", as in Telugu crew scripts)
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = hp.add_run(); set_run_font(r, V3_LATIN, 9)
    for tag, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), tag); r._element.append(fc)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._element.append(it)
    pg = OxmlElement("w:pgNumType"); pg.set(qn("w:start"), "1"); sec._sectPr.append(pg)

    table, missing = None, []
    first = True
    for u in v3_layout(doc_json, latin):
        if u["kind"] == "heading":
            table = None
            left, loc, time = u["cols"]
            p = doc.add_paragraph()
            v3_para_fmt(p, before=0 if first else 22, after=12, line=16, keep_next=True)
            p.paragraph_format.tab_stops.add_tab_stop(Inches(W / 2), WD_TAB_ALIGNMENT.CENTER)
            p.paragraph_format.tab_stops.add_tab_stop(Inches(W), WD_TAB_ALIGNMENT.RIGHT)
            v3_text(p, f"{left}\t{loc}\t{time}", 12, 11, bold=True)
        elif u["kind"] == "transition":                          # (only when no row precedes it)
            table = None
            p = doc.add_paragraph(); v3_para_fmt(p, align=WD_ALIGN_PARAGRAPH.RIGHT, before=6, after=10)
            v3_text(p, u["text"])
        else:
            if table is None:
                table = doc.add_table(rows=0, cols=3)
                table.autofit = False
                tblPr = table._tbl.tblPr
                lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
                for k, gc in enumerate(table._tbl.tblGrid.findall(qn("w:gridCol"))):
                    gc.set(qn("w:w"), str(int(COLS[k] * 1440)))
            row = table.add_row()
            trPr = row._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); trPr.append(cs)
            v3_cell(row.cells[0], u["left"], COLS[0])
            v3_cell(row.cells[1], u["name"], COLS[1], align=WD_ALIGN_PARAGRAPH.RIGHT)
            v3_cell(row.cells[2], u["dlg"], COLS[2])
            if u.get("trans"):                                 # CUT TO: lives in the scene's last row
                c = row.cells[2]
                if not u["dlg"]:
                    v = OxmlElement("w:vAlign"); v.set(qn("w:val"), "bottom"); c._tc.get_or_add_tcPr().append(v)
                    tp_ = c.paragraphs[0]
                else:
                    tp_ = c.add_paragraph()
                v3_para_fmt(tp_, align=WD_ALIGN_PARAGRAPH.RIGHT, before=8, after=10)
                v3_text(tp_, u["trans"])
            table = None if u.get("trans") else table
        first = False
    if not latin:
        for e in doc_json["elements"]:
            if e["type"] != "character" and not e.get("te"):
                missing.append(e["text"][:30])
        for e in {e["text"] for e in doc_json["elements"] if e["type"] == "character"} - set(doc_json.get("names_te", {})):
            missing.append("name " + e)
    doc.save(out)
    if missing:
        print(f"WARNING: {len(missing)} item(s) without Telugu (English kept): {missing[:5]}")
    print(f"wrote {out}")


def to_pdf(data, docx_path, **kw):
    """PDF is rendered from a twin .docx set in Courier Prime (same 10-pitch metrics as
    Courier New, so pagination is identical) when that font is installed."""
    import tempfile, shutil, os
    global FONT
    final = pathlib.Path(docx_path).with_suffix(".pdf")
    tmp = pathlib.Path(tempfile.mkdtemp())
    twin = tmp / (final.stem + ".docx")
    try:
        has_prime = "Courier Prime" in subprocess.run(["fc-list"], capture_output=True, text=True).stdout
    except FileNotFoundError:           # macOS/Windows without fontconfig: trust the installed fonts
        has_prime = True
    saved = FONT
    if has_prime:
        FONT = "Courier Prime"
    (render_v3(data, str(twin), latin=kw.get("latin", False)) if kw.get("v3")
     else render(data, str(twin), **{k: v for k, v in kw.items() if k not in ("v3", "latin")}))
    FONT = saved
    subprocess.run([find_soffice(), "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(twin)],
                   check=True, capture_output=True)
    shutil.move(str(tmp / (final.stem + ".pdf")), str(final))
    pdf = str(final)
    print(f"wrote {pdf}")
    return pdf


if __name__ == "__main__":
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    kw = dict(telugu="--telugu" in sys.argv, full="--telugu-full" in sys.argv,
              scene_numbers="--no-scene-numbers" not in sys.argv)
    if "--v3" in sys.argv or "--v4" in sys.argv:
        kw["v3"] = True
        kw["latin"] = "--v4" in sys.argv
        render_v3(data, out, latin=kw["latin"])
    else:
        render(data, out, **kw)
    if "--pdf" in sys.argv:
        to_pdf(data, out, **kw)
