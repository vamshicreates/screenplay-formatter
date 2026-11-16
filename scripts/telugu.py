#!/usr/bin/env python3
"""Telugu-letters mode helpers.

V1 (dialogue only):
  telugu.py export <script.json> <lines.json>       list every dialogue line (index, speaker, text)
  telugu.py merge  <script.json> <te.json>          te.json = {"<index>": "<Telugu text>", ...}; adds "te"
  telugu.py check  <script.json>                    validate the Telugu dialogue lines
V2 (full Telugu — everything except character names), add --all to each command:
  export --all lists every element except character cues, plus title-page lines with keys
  "tp.title", "tp.center.<n>", "tp.contact.<n>"; merge accepts those keys; check --all validates all.

Checks (per dialogue line):
  - Telugu text present and actually in Telugu script
  - no Latin letters left (digits and punctuation are fine)
  - same number of words as the Tinglish line (word-for-word, no translation / omission)
  - sound-alike check: the Telugu, romanised back, should resemble the Tinglish word;
    low matches are listed for Claude to double-check (English loanwords often show up — fine if correct)
Exit 1 if any hard error (missing / Latin left); word-count and sound-alike items are review flags.
"""
import json, re, sys, difflib

TE = re.compile(r"[ఀ-౿]")
LATIN = re.compile(r"[A-Za-z]")


def words(s):
    return [w for w in re.split(r"[\s\-–—]+", re.sub(r"[^\w\s\-–—ఀ-౿]", " ", s)) if w.strip()]


def skeleton(s):
    s = s.lower()
    for a, b in (("ph", "f"), ("th", "t"), ("dh", "d"), ("kh", "k"), ("gh", "g"), ("ch", "c"), ("sh", "s"),
                 ("bh", "b"), ("jh", "j"), ("w", "v"), ("z", "j"), ("q", "k"), ("x", "ks"), ("y", "")):
        s = s.replace(a, b)
    s = re.sub(r"[aeiouh]", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s.replace("f", "p")


def romanise(te):
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        r = transliterate(te, sanscript.TELUGU, sanscript.HK)
    except Exception:
        return None
    r = r.replace("M", "n").replace("R", "r").replace("z", "s").replace("S", "s").replace("T", "t").replace("D", "d").replace("N", "n")
    return r


def items(doc, full):
    """Yield (key, english, telugu, label) for every line that should be in Telugu."""
    els = doc["elements"]
    speaker = None
    if full and doc.get("title_page"):
        tp = doc["title_page"]
        yield "tp.title", tp.get("title", ""), tp.get("title_te"), "title"
        for part in ("center", "contact"):
            tes = tp.get(part + "_te") or []
            for n, l in enumerate(tp.get(part, [])):
                yield f"tp.{part}.{n}", l, (tes[n] if n < len(tes) else None), "title page"
    for i, e in enumerate(els):
        if e["type"] == "character":
            speaker = e["text"]; continue
        if e["type"] == "dialogue" or full:
            yield str(i), e["text"], e.get("te"), (speaker if e["type"] == "dialogue" else e["type"])


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    full = "--all" in sys.argv
    args = [a for a in sys.argv[3:] if a != "--all"]
    doc = json.load(open(path, encoding="utf-8"))
    els = doc["elements"]
    if cmd == "export":
        rows = [{"key": k, "kind": lab, "text": en} for k, en, te, lab in items(doc, full)]
        json.dump(rows, open(args[0], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"exported {len(rows)} lines -> {args[0]}")
    elif cmd == "merge":
        te = json.load(open(args[0], encoding="utf-8"))
        n = 0
        for k, v in te.items():
            if k.startswith("tp."):
                tp = doc["title_page"]
                parts = k.split(".")
                if parts[1] == "title":
                    tp["title_te"] = v
                else:
                    lst = tp.setdefault(parts[1] + "_te", [None] * len(tp.get(parts[1], [])))
                    lst[int(parts[2])] = v
            else:
                i = int(k)
                assert els[i]["type"] != "character", f"element {i} is a character name — those stay English"
                if not full:
                    assert els[i]["type"] == "dialogue", f"element {i} is {els[i]['type']}, not dialogue (use --all for full Telugu)"
                els[i]["te"] = v
            n += 1
        json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"merged {n} Telugu lines into {path}")
    elif cmd == "check":
        hard, review = [], []
        total = 0
        for k, en, te, lab in items(doc, full):
            total += 1
            te = te or ""
            if not te or not TE.search(te):
                hard.append(f"#{k} ({lab}): no Telugu text — “{en[:60]}”"); continue
            if LATIN.search(te):
                hard.append(f"#{k} ({lab}): Latin letters left: {''.join(sorted(set(LATIN.findall(te))))} — “{te[:60]}”")
            ew, tw = words(en), words(te)
            if len(ew) != len(tw):
                review.append(f"#{k} ({lab}): word count {len(ew)} → {len(tw)}  | {en}  ⇒  {te}")
            elif romanise(te) is not None:
                for a, b in zip(ew, tw):
                    rb = romanise(b) or ""
                    ra, rr = skeleton(a), skeleton(rb)
                    if ra and rr and difflib.SequenceMatcher(a=ra, b=rr).ratio() < 0.5:
                        review.append(f"#{k}: “{a}” → “{b}” ({rb}) — sounds different, confirm it's a transliteration not a translation")
        print(f"lines checked: {total} ({'full Telugu' if full else 'dialogue only'})")
        for h in hard:
            print("ERROR  " + h)
        for r in review:
            print("REVIEW " + r)
        if hard:
            print(f"FAIL — {len(hard)} error(s)"); sys.exit(1)
        print(f"PASS — all lines in Telugu letters; {len(review)} item(s) to review" if review else "PASS — all lines in Telugu letters, word for word")


if __name__ == "__main__":
    main()
