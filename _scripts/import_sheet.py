#!/usr/bin/env python3
"""Snapshot the Google song sheet and the Google Site home page into data/songs.csv.

One row per song. Rows come from the sheet first, then songs linked only from
the Google Site home page. The kid-song lists on the home page become the
`kids` and `kids-motions` libraries.

Run from the repository root:  python3 _scripts/import_sheet.py
"""

import csv
import html
import io
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

SHEET_ID = "1J4-ljjHTRQOX2olV-pJLCB6aqwrzKT2Yxj2s_01-tLM"
SITE_HOME = "https://www.ukeskywalker.com/home"
OUT = Path("data/songs.csv")

# Sheet column letter -> field name. Column A (an old PDF page number) is dropped.
COLUMNS = {
    "B": "sheet_title", "C": "artist", "D": "docs_label", "E": "key",
    "F": "low", "G": "high", "H": "difficulty", "I": "practice", "J": "fun",
    "K": "skill", "L": "poppy", "M": "happy", "N": "spiritual",
    "O": "protest", "P": "added", "Q": "pages",
}
FIELDS = ["sheet_title", "artist", "doc_id", "docs_label", "other_links", "key",
          "low", "high", "difficulty", "practice", "fun", "skill", "poppy",
          "happy", "spiritual", "protest", "added", "pages", "source", "libraries"]

HYPERLINK = re.compile(r'hyperlink\("([^"]*)"\s*[,;]\s*"([^"]*)"\)', re.I)
DOC_ID = re.compile(r"/document/d/([A-Za-z0-9_-]+)")


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def read_sheet():
    """Return a list of dicts, one per sheet row, with links pulled out of formulas."""
    base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
    values = list(csv.reader(io.StringIO(fetch(base + "?format=csv&gid=0").decode("utf-8"))))
    xlsx = zipfile.ZipFile(io.BytesIO(fetch(base + "?format=xlsx")))
    sheet_xml = xlsx.read("xl/worksheets/sheet1.xml").decode("utf-8")

    # cell ref -> link target, from HYPERLINK formulas
    links = {}
    for ref, body in re.findall(r'<c r="([A-Z]+\d+)"[^>]*>(.*?)</c>', sheet_xml, re.S):
        f = re.search(r"<f>(.*?)</f>", body, re.S)
        if f:
            m = HYPERLINK.search(html.unescape(f.group(1)))
            if m:
                links[ref] = m.group(1)

    letters = "ABCDEFGHIJKLMNOPQ"
    rows = []
    for i, cells in enumerate(values[1:], start=2):
        row = {name: "" for name in FIELDS}
        for col, name in COLUMNS.items():
            j = letters.index(col)
            row[name] = cells[j].strip() if j < len(cells) else ""
        title_link = links.get(f"B{i}", "")
        m = DOC_ID.search(title_link)
        row["doc_id"] = m.group(1) if m else ""
        other = [links[f"{c}{i}"] for c in "D" if f"{c}{i}" in links]
        if title_link and not m:
            other.insert(0, title_link)
        row["other_links"] = " ".join(other)
        row["source"] = "sheet"
        rows.append(row)
    return rows


def read_site():
    """Return (kid doc ids, kid-motion doc ids, {doc_id: link text}) from the home page."""
    page = fetch(SITE_HOME).decode("utf-8", errors="ignore")
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)

    def section(start, end):
        i = page.find(start)
        j = page.find(end, i + 1) if end else -1
        return page[i:j] if i >= 0 else ""

    def docs_in(chunk):
        found = {}
        for href, text in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S):
            m = DOC_ID.search(html.unescape(href))
            if m:
                label = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
                found.setdefault(m.group(1), label)
        return found

    motions = docs_in(section("Dance Moves or Motions", "All Kid-Friendly Songs"))
    kids = docs_in(section("All Kid-Friendly Songs", "Songs to add"))
    return kids, motions


def norm(title):
    """Compare titles loosely: case, punctuation, a leading or trailing 'The'."""
    t = re.sub(r"[^a-z0-9 ]", "", title.lower().replace("’", "'"))
    t = re.sub(r"^the |\s+the$", "", t.strip())
    return re.sub(r"\s+", "", t)


def main():
    rows = read_sheet()
    kids, motions = read_site()
    by_doc = {r["doc_id"]: r for r in rows if r["doc_id"]}

    by_title = {norm(r["sheet_title"]): r for r in rows if not r["doc_id"]}
    for doc_id, label in {**kids, **motions}.items():
        if doc_id in by_doc:
            continue
        match = by_title.pop(norm(label), None)
        if match:  # sheet row with no link; the site has its Doc
            match["doc_id"] = doc_id
            by_doc[doc_id] = match
        else:
            row = {name: "" for name in FIELDS}
            row.update(sheet_title=label, doc_id=doc_id, source="site")
            rows.append(row)
            by_doc[doc_id] = row

    for row in rows:
        libs = ["all"]
        try:
            if float(row["spiritual"] or 0) >= 1:
                libs.append("spiritual")
        except ValueError:
            pass
        if row["artist"].strip().lower() == "andy stein":
            libs.append("andy-original")
        if "yeastbombs" in row["artist"].lower():
            libs.append("yeastbombs")
        if row["doc_id"] in kids or row["doc_id"] in motions:
            libs.append("kids")
        if row["doc_id"] in motions:
            libs.append("kids-motions")
        row["libraries"] = " ".join(libs)

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    site_only = sum(r["source"] == "site" for r in rows)
    print(f"{len(rows)} songs ({site_only} from the site only) -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
