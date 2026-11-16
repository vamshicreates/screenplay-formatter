#!/usr/bin/env python3
"""Cross-check 4 (prep) — split the job into review packets for independent reviewers.

Usage: review_packets.py <source.txt> <script.json> <checks/fidelity.json> <outdir> [--mode en|te|full] [--pages 12]

Each packet = a run of original pages (default 12) with:
  - the ORIGINAL text of those pages exactly as read from the file
  - every formatted element mapped to those pages: index, type, English text, and Telugu (when the mode has it)
Packets are Markdown files a reviewer can read top to bottom. Also writes <outdir>/index.json.
Run check_fidelity.py with --report first (it gives each element's source page).
"""
import json, os, sys


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    src, sj, fj, outdir = args[:4]
    mode = sys.argv[sys.argv.index("--mode") + 1] if "--mode" in sys.argv else "en"
    per = int(sys.argv[sys.argv.index("--pages") + 1]) if "--pages" in sys.argv else 12
    pages = open(src, encoding="utf-8").read().split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    doc = json.load(open(sj, encoding="utf-8"))
    epages = json.load(open(fj, encoding="utf-8"))["element_pages"]
    els = doc["elements"]
    os.makedirs(outdir, exist_ok=True)
    index = []
    n = len(pages)
    for start in range(1, n + 1, per):
        end = min(n, start + per - 1)
        k = len(index) + 1
        lines = [f"# Review packet {k}: original pages {start}–{end} of {n}  (mode: {mode})", ""]
        if start == 1 and doc.get("title_page"):
            tp = doc["title_page"]
            lines += ["## Title page (formatted)", f"- title: {tp.get('title','')}" + (f"  ⇒  {tp.get('title_te','')}" if mode == 'full' else "")]
            for part in ("center", "contact"):
                tes = tp.get(part + "_te") or []
                for i, l in enumerate(tp.get(part, [])):
                    lines.append(f"- {part}: {l}" + (f"  ⇒  {tes[i] if i < len(tes) else '(missing)'}" if mode == 'full' else ""))
            lines.append("")
        lines += ["## ORIGINAL (as read from the file)", ""]
        for p in range(start, end + 1):
            lines += [f"----- original page {p} -----", "```", pages[p - 1].rstrip(), "```", ""]
        lines += ["## FORMATTED elements for these pages", "",
                  "Format: `#index [type] English text` and, where the mode has Telugu, `  ⇒ Telugu` on the next line.", ""]
        idxs = [i for i, pg in enumerate(epages) if start <= pg <= end]
        for i in idxs:
            e = els[i]
            num = f" ({e['number']})" if e.get("number") else ""
            lines.append(f"#{i} [{e['type']}{num}] {e['text']}")
            show_te = (mode == "full" and e["type"] != "character") or (mode in ("te", "full") and e["type"] == "dialogue")
            if show_te:
                lines.append(f"    ⇒ {e.get('te', '(MISSING TELUGU)')}")
        path = os.path.join(outdir, f"packet_{k:02d}.md")
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        index.append({"packet": k, "file": path, "pages": [start, end], "elements": [idxs[0], idxs[-1]] if idxs else []})
    json.dump(index, open(os.path.join(outdir, "index.json"), "w"), indent=1)
    print(f"{len(index)} packet(s) in {outdir}: " + ", ".join(f"p{x['pages'][0]}–{x['pages'][1]}" for x in index))


if __name__ == "__main__":
    main()
