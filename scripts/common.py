"""Shared helpers: tokenising, page mapping and source↔output alignment for the cross-checks."""
import difflib, re

PAGE_NUM = re.compile(r"^\s*\(?\d{1,3}\)?\s*\.?\s*$")
TOK = re.compile(r"[a-z0-9ఀ-౿]+")
ALLOWED_DROP = {"scene"}          # "SCENE 4" → number moves to the margins
ALLOWED_ADD = {"to"}              # "CUT" → "CUT TO:"
EXT_RE = r"\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D)\)"


def toks(s):
    s = s.lower().replace("’", "'").replace("'", "").replace("‌", "").replace("‍", "")
    return TOK.findall(s)


def source_tokens(src_text, cue_names):
    """Tokens of the original, each with its page number; speaker cues pulled out separately.
    Returns (tokens, pages, cues, page_count)."""
    pages_text = src_text.split("\f")
    tokens, pages, cues = [], [], []
    alt = "|".join(re.escape(n) for n in sorted(set(cue_names), key=len, reverse=True))
    cue_re = re.compile(rf"(?m)^[ \t]*({alt})[ \t]*({EXT_RE})?[ \t]*(:|$)") if alt else None
    for pno, ptxt in enumerate(pages_text, start=1):
        lines = [l for l in ptxt.split("\n") if not PAGE_NUM.match(l) or not l.strip()]
        ptxt = "\n".join(lines)
        if cue_re:
            def grab(m):
                cues.append((m.group(1).upper(), pno))
                return " "
            ptxt = cue_re.sub(grab, ptxt)
        for t in toks(ptxt):
            tokens.append(t); pages.append(pno)
    return tokens, pages, cues, len(pages_text)


def output_tokens(doc):
    """Tokens of script.json in reading order (cues excluded), each tagged with its element index
    (-1 for title page)."""
    out, owner = [], []
    tp = doc.get("title_page") or {}
    if tp:
        for l in [tp.get("title", "")] + tp.get("center", []) + tp.get("contact", []):
            for t in toks(l):
                out.append(t); owner.append(-1)
    for i, e in enumerate(doc["elements"]):
        if e["type"] == "character":
            continue
        parts = ([e["number"]] if e["type"] == "scene_heading" and e.get("number") else []) + [e["text"]]
        for p in parts:
            for t in toks(p):
                out.append(t); owner.append(i)
    return out, owner


def align(src, out):
    """Return (problems, src_ok[list of bool], out_src_index[list: source index or None])."""
    sm = difflib.SequenceMatcher(a=src, b=out, autojunk=False)
    src_ok = [False] * len(src)
    out_map = [None] * len(out)
    problems = []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        gone, added = src[a1:a2], out[b1:b2]
        if op == "equal":
            for k in range(a2 - a1):
                src_ok[a1 + k] = True; out_map[b1 + k] = a1 + k
            continue
        allowed = ((op == "delete" and set(gone) <= ALLOWED_DROP) or
                   (op == "insert" and set(added) <= ALLOWED_ADD) or
                   (op == "replace" and set(gone) <= ALLOWED_DROP and set(added) <= ALLOWED_ADD))
        if allowed:
            for k in range(a1, a2):
                src_ok[k] = True
            for k in range(b1, b2):
                out_map[k] = a1 if a1 < len(src) else (a1 - 1 if a1 else None)
            continue
        problems.append((op, a1, a2, b1, b2))
        for k in range(b1, b2):
            out_map[k] = a1 if a1 < len(src) else (a1 - 1 if a1 else None)
    return problems, src_ok, out_map


def element_pages(doc, src_pages, out_owner, out_map):
    """Source page for every element (first mapped token wins; cues/empty inherit from neighbours)."""
    n = len(doc["elements"])
    page = [None] * n
    for k, i in enumerate(out_owner):
        if i >= 0 and page[i] is None and out_map[k] is not None:
            page[i] = src_pages[out_map[k]]
    # character names belong with the dialogue that follows them; anything else inherits backwards
    for i in range(n - 1, -1, -1):
        if page[i] is None and doc["elements"][i]["type"] == "character" and i + 1 < n:
            page[i] = page[i + 1]
    last = 1
    for i in range(n):
        if page[i] is None:
            page[i] = last
        last = page[i]
    return page


# ---------------------------------------------------------------- V3 (Telugu two-column layout)
def v3_heading(e):
    """('4.INT', 'KARTHIK ROOM/HALL', '-DAY/MORNING') from an English scene-heading element."""
    import re as _re
    t = e["text"].upper().strip()
    m = _re.match(r"^(INT\./EXT\.|EXT\./INT\.|INT\.|EXT\.|I/E\.?)\s*(.*)$", t)
    ie, rest = (m.group(1), m.group(2)) if m else ("", t)
    ie = ie.replace(".", "")
    loc, time = rest, ""
    if " - " in rest:
        loc, time = rest.rsplit(" - ", 1)
    num = e.get("number", "")
    left = f"{num}.{ie}" if num and ie else (num or ie)
    return left, loc.strip(), (f"-{time.strip()}" if time else "")


def _strip_brackets(s):
    s = s.strip()
    return s[1:-1].strip() if s.startswith("(") and s.endswith(")") else s


def v3_rows(doc):
    """Reading-order units of the V3 layout:
      {"kind": "heading", "cols": (left, loc, time), "idx": [i]}
      {"kind": "row", "left": str, "name": str, "dlg": str, "idx": [...]}     (action and/or speech)
      {"kind": "transition", "text": str, "idx": [i]}
    Text is Telugu ("te"); character names come from doc["names_te"]. An action element with
    "v3_beside": true is printed in the left column beside the next speech; parentheticals of a speech
    go there too (brackets dropped). Everything else in the left column stands on its own row."""
    els = doc["elements"]
    names = doc.get("names_te", {})
    te = lambda e: e.get("te") or e["text"]
    units, pending, speaker = [], [], None
    i = 0
    while i < len(els):
        e = els[i]
        t = e["type"]
        if t == "scene_heading":
            for p in pending:
                units.append({"kind": "row", "left": te(els[p]), "name": "", "dlg": "", "idx": [p]})
            pending = []
            units.append({"kind": "heading", "cols": v3_heading(e), "idx": [i]}); speaker = None
        elif t == "transition":
            for p in pending:
                units.append({"kind": "row", "left": te(els[p]), "name": "", "dlg": "", "idx": [p]})
            pending = []
            units.append({"kind": "transition", "text": te(e), "idx": [i]})
        elif t == "action":
            nxt = els[i + 1]["type"] if i + 1 < len(els) else None
            if e.get("v3_beside") and nxt in ("character", "action"):
                pending.append(i)
            else:
                for p in pending:
                    units.append({"kind": "row", "left": te(els[p]), "name": "", "dlg": "", "idx": [p]})
                pending = []
                units.append({"kind": "row", "left": te(e), "name": "", "dlg": "", "idx": [i]})
        elif t == "character":
            speaker = i
        elif t in ("parenthetical", "dialogue"):
            # gather parentheticals up to the dialogue they introduce
            lefts, idx = [te(els[p]) for p in pending], list(pending) + ([speaker] if speaker is not None else [])
            pending = []
            j = i
            while j < len(els) and els[j]["type"] == "parenthetical":
                lefts.append(_strip_brackets(te(els[j]))); idx.append(j); j += 1
            dlg = ""
            if j < len(els) and els[j]["type"] == "dialogue":
                dlg = te(els[j]); idx.append(j)
            else:
                j -= 1
            nm = names.get(els[speaker]["text"], els[speaker]["text"]) if speaker is not None else ""
            units.append({"kind": "row", "left": "\n".join(lefts), "name": f"{nm} :" if nm else "", "dlg": dlg, "idx": idx})
            i = j
        i += 1
    for p in pending:
        units.append({"kind": "row", "left": te(els[p]), "name": "", "dlg": "", "idx": [p]})
    return units


def v3_layout(doc):
    """v3_rows() with each transition folded into the row before it ("trans" key), so CUT TO: can never be
    stranded at the top of a page (a table row is never split). Used by both render.py and check_output.py."""
    out = []
    for u in v3_rows(doc):
        if u["kind"] == "transition" and out and out[-1]["kind"] == "row" and "trans" not in out[-1]:
            out[-1] = dict(out[-1], trans=u["text"], idx=out[-1]["idx"] + u["idx"])
        else:
            out.append(u)
    return out
