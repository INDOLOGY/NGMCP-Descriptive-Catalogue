#!/usr/bin/env python3
"""Build the search index for the NGMCP Descriptive Catalogue.

Reads every catalogue page in docs/ and writes two files used by
docs/index.html (the search page):

  docs/search/records.json   one short record per manuscript (fields below)
  docs/search/excerpts.json  the Beginning / End / Colophon text of each
                             record, loaded only when a user ticks
                             "also search excerpts"

Run it again whenever pages are added or changed:

    python3 tools/build_search_index.py
"""
import html
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
OUT = os.path.join(ROOT, "search")

# Short keys keep the index small; the search page maps them back to labels.
INFOBOX = {            # label in the infobox -> key
    "Filmed in": "reel",
    "Title": "title",
    "Subjects": "subj",
    "Languages": "lang",
    "Scripts": "script",
    "Material": "mat",
    "Date": "date",
    "Acc No.": "acc",
    "Dimensions": "dim",
    "Condition": "cond",
}
MAIN = {               # label in the main description -> key (used if not in infobox)
    "Author": "auth",
    "Scribe": "scribe",
    "Place of Copying": "place",
    "King": "king",
    "Place of Deposit": "dep",
    "Date of Copying": "date",
}

TAG = re.compile(r"<[^>]+>")
SPACE = re.compile(r"\s+")
PLACEHOLDER = re.compile(r"^\{\{\{.*\}\}\}$")   # unfilled wiki template, e.g. {{{languages}}}
STRIP = " :" + chr(0xA0)


def clean(s):
    s = TAG.sub(" ", s)
    s = html.unescape(s)
    s = SPACE.sub(" ", s).strip(STRIP)
    return "" if PLACEHOLDER.match(s) else s


def section(body, start_id, end_ids):
    m = re.search(r'id="%s"' % re.escape(start_id), body)
    if not m:
        return ""
    rest = body[m.end():]
    end = len(rest)
    for e in end_ids:
        k = rest.find('id="%s"' % e)
        if k != -1:
            end = min(end, k)
    return re.sub(r"<[^>]*$", "", rest[:end])            # drop a half-cut tag at the end


def parse(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r'id="mw-content-text"(.*?)<!--\s*\nNewPP', t, re.S)
    body = m.group(1) if m else t
    rec = {}
    h1 = re.search(r'id="firstHeading"[^>]*>(.*?)</h1>', t, re.S)
    rec["name"] = clean(h1.group(1)) if h1 else os.path.basename(path)[:-5]

    box = section(body, "Manuscript_culture_infobox", ["Manuscript_Details"])
    for label, key in INFOBOX.items():
        mm = re.search(r"<b>%s</b>:(.*?)(?:<br\s*/?>|</p>)" % re.escape(label), box, re.S)
        if mm:
            v = clean(mm.group(1))
            if v:
                rec[key] = v

    for label, key in MAIN.items():
        if key in rec:
            continue
        mm = re.search(r"<p><b>%s:?</b>(.*?)</p>" % re.escape(label), body, re.S)
        if mm:
            v = clean(mm.group(1))
            if v:
                rec[key] = v

    exc = section(body, "Excerpts", ["Microfilm_Details"])
    exc = re.sub(r"^[^<]*</span>\s*</h2>", "", exc)       # drop the section heading itself
    exc = clean(re.sub(r"</p>|<br\s*/?>", " ", exc))
    return rec, exc


def main():
    files = sorted(f for f in os.listdir(ROOT)
                   if f.endswith(".html") and f not in ("index.html", "list.html"))
    records, excerpts = [], []
    for f in files:
        rec, exc = parse(os.path.join(ROOT, f))
        rec["file"] = f
        records.append(rec)
        excerpts.append(exc)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "records.json"), "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "excerpts.json"), "w", encoding="utf-8") as fh:
        json.dump(excerpts, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(records)} records written to {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
