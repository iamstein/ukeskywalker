#!/usr/bin/env python3
"""Turn data/songs.csv and the song Google Docs into songs/<slug>.qmd.

A one-time migration. Each Doc is downloaded as plain text into data/raw/
(not committed). A song file that has been edited since this script wrote it
is left alone; pass --force SLUG to re-import one song anyway. Anything the
script could not read cleanly is listed in data/import-report.md.

Run from the repository root:
    python3 _scripts/import_docs.py            # download missing Docs, write songs
    python3 _scripts/import_docs.py --offline  # use data/raw/ only
    python3 _scripts/import_docs.py --force abigail-belle-of-kilronan
"""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

SONGS = Path("songs")
FILES = SONGS / "files"
RAW = Path("data/raw")
HASHES = Path("data/import-hashes.csv")
REPORT = Path("data/import-report.md")

# A chord is a root note plus any suffix, so Andy's own marks (C', Fh, Bb*) count.
CHORD = re.compile(r"^[A-G][#b]?[^\s,;\[\]]*$")
LABEL = re.compile(r"^(verse|chorus|bridge|intro|outro|pre-?chorus|interlude|ending|end|"
                   r"instrumental|refrain|solo|coda|tag|break|hook|verses?)\b[^\[\]]{0,30}$", re.I)
YOUTUBE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/\S+|youtu\.be/\S+)")
MELODY_START = re.compile(r"^([0-7#b(+]|\(|melody\b|same\b|repeat\b)", re.I)
# Notes are [#b]?degree, optional m (lowered), octave marks; joined by - , ; . = / or nothing.
MELODY_TOKEN = re.compile(r"^(?:[#b]?[0-7]m?(?:\.+|'+)?[-,;.=/~…]*)+$")


# ---------- small helpers ----------

def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"\([^)]*\)", "", text).replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "song"


def deinvert(name):
    """'Banana Boat Song, The' -> 'The Banana Boat Song'."""
    m = re.match(r"^(.*), (The|A|An)$", name.strip())
    return f"{m.group(2)} {m.group(1)}" if m else name.strip()


def invert(name):
    """'The Banana Boat Song' -> 'Banana Boat Song, The', for sorting."""
    m = re.match(r"^(The|A|An) (.*)$", name.strip())
    return f"{m.group(2)}, {m.group(1)}" if m else name.strip()


def norm(text):
    return re.sub(r"[^a-z0-9]", "", deinvert(text).lower())


def number(value):
    value = value.strip()
    if not value:
        return None
    try:
        f = float(value)
    except ValueError:
        return value
    return int(f) if f.is_integer() else f


def straight_quotes(s):
    return (s.replace("’", "'").replace("‘", "'")
             .replace("“", '"').replace("”", '"').replace(" ", " "))


def is_chord_list(inside):
    parts = [p for p in re.split(r"[,;\s]+", inside.strip()) if p]
    return bool(parts) and all(CHORD.match(p) for p in parts)


def is_label(line):
    """'Verse 1', 'Chorus (x2)', 'Bridge:' -- but not 'Intro: C C G F'."""
    s = line.strip()
    return (bool(LABEL.match(s)) and "[" not in s and len(s) <= 30
            and (":" not in s or s.endswith(":")))


def first_chord(lines):
    for line in lines:
        for inside in re.findall(r"\[([^\]]+)\]", line):
            if is_chord_list(inside):
                return re.split(r"[,;\s/]+", inside.strip())[0]
    return None


def voice(value, report, slug):
    """'2 E' -> 'E2'; '4 C#' -> 'C#4'."""
    value = value.strip().split("\n")[0].strip()  # two lines = two keys; the first goes with `key`
    if not value or value == "-":
        return None
    m = re.fullmatch(r"(\d)\s*([A-Ga-g][#b]?)", value)
    if m:
        return m.group(2).upper()[0] + m.group(2)[1:] + m.group(1)
    report.append((slug, f"voice range `{value}` not converted; kept as written"))
    return value


def key_name(value):
    value = value.strip().rstrip("?").strip()
    m = re.match(r"^([A-Ga-g][#b]?)\s*(m|minor|M|major)?\b", value)
    if not m:
        return None
    root = m.group(1)[0].upper() + m.group(1)[1:]
    return root + ("m" if m.group(2) in ("m", "minor") else "")


# ---------- reading one Doc ----------

def split_melody(line):
    """Split 'lyrics        3 2 1' at the first wide gap followed by melody."""
    m = re.search(r"\S( {3,}|\t+)(\S.*)$", line)
    if not m:
        return line.rstrip(), None
    rest = m.group(2).strip()
    if not MELODY_START.match(rest):
        return line.rstrip(), None
    return line[: m.start(1)].rstrip(), rest


def clean_melody(melody):
    return re.sub(r"[’‘`´]", "'", melody).strip()


def odd_melody_tokens(melody):
    if re.fullmatch(r"\(.*\)|\+*|melody", melody, re.I):
        return []
    tokens = re.sub(r"\([^)]*\)", " ", melody).split()
    return [t for t in tokens if not MELODY_TOKEN.match(t) and t not in ("|", "+", "x2", "2x")]


def parse_doc(text, slug, report):
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    # Split off later copies of the song (a line of underscores, then the title again).
    copies, current = [], []
    for line in lines:
        if re.fullmatch(r"\s*_{5,}\s*", line):
            copies.append(current)
            current = []
        else:
            current.append(line)
    copies.append(current)
    main = copies[0]
    title_line = next((l.strip() for l in main if l.strip()), "")
    alt_keys, extra = [], []
    for copy in copies[1:]:
        head = next((l.strip() for l in copy if l.strip()), "")
        if not head:
            continue
        if norm(head.split(" - ")[0]) == norm(title_line.split(" - ")[0]):
            k = next((key_name(l.split("Key of", 1)[1]) for l in copy[:6] if "Key of" in l), None)
            if k:
                alt_keys.append(k)
            report.append((slug, f"second copy of the song (key {k or '?'}) dropped; the key menu replaces it"))
        else:
            extra.append(copy)
            report.append((slug, "text after a `____` line kept as more of the song; check it"))
    for copy in extra:
        main += [""] + copy

    info = {"doc_title": title_line, "key": None, "key_note": None, "youtube": None,
            "alt_keys": alt_keys}
    body = []
    header_done = False
    pending_youtube_label = False
    for i, raw in enumerate(main):
        if i == 0 and raw.strip() == title_line:
            continue
        line = straight_quotes(raw).rstrip()
        stripped = line.strip()

        if not header_done:
            yt = YOUTUBE.search(stripped)
            if yt and not info["youtube"] and (stripped.lower().startswith(("youtube", "http", "ukulele")) or pending_youtube_label):
                info["youtube"] = yt.group(0)
                pending_youtube_label = False
                continue
            if re.fullmatch(r"youtube( link)?:?", stripped, re.I):
                pending_youtube_label = True
                continue
            km = re.match(r"^key of\s+(.+)$", stripped, re.I)
            if km and not info["key"]:
                info["key"] = key_name(km.group(1))
                note = re.sub(r"^[A-Ga-g][#b]?m?\??\s*", "", km.group(1)).strip()
                if note:
                    info["key_note"] = note.strip("() ")
                continue
            if "[" in stripped or is_label(split_melody(stripped)[0]):
                header_done = True

        lyrics, melody = split_melody(line)
        if lyrics.strip().lower() in ("lyrics", "lyric", "") and melody and melody.lower().startswith("melody"):
            continue
        if melody and melody.lower().startswith("melody"):
            melody = None
        if is_label(lyrics):
            lyrics = lyrics.strip().rstrip(":") + ":"
        if lyrics.strip().startswith("#"):
            lyrics = "\\" + lyrics.strip()  # a literal '#', not a note line
        if " | " in lyrics:
            report.append((slug, f"lyrics contain ` | `, which marks the melody: `{lyrics.strip()[:60]}`"))
        if melody:
            melody = clean_melody(melody)
            odd = odd_melody_tokens(melody)
            if odd:
                report.append((slug, f"melody tokens outside the notation: `{' '.join(odd)}` in `{melody[:50]}`"))
            body.append(f"{lyrics} | {melody}" if lyrics.strip() else f"| {melody}")
        else:
            body.append(lyrics)

    # Trim and squeeze blank lines.
    out, blank = [], 0
    for line in body:
        blank = blank + 1 if not line.strip() else 0
        if blank <= 1:
            out.append(line)
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    info["body"] = out
    info["has_melody"] = any(" | " in l or l.startswith("| ") for l in out)
    return info


# ---------- downloads ----------

def download(url, dest):
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return e.code
    if data[:15].lstrip().lower().startswith((b"<!doctype", b"<html")):
        return 401
    dest.write_bytes(data)
    return 200


def fetch_doc(doc_id, offline):
    path = RAW / f"{doc_id}.txt"
    if not path.exists() and not offline:
        RAW.mkdir(parents=True, exist_ok=True)
        download(f"https://docs.google.com/document/d/{doc_id}/export?format=txt", path)
    if path.exists() and not path.read_bytes()[:200].lstrip().startswith(b"<"):
        return path.read_text(encoding="utf-8-sig", errors="replace")
    return None


def fetch_spreadsheet(url, slug, offline, report):
    m = re.search(r"key=([A-Za-z0-9_-]+)", url) or re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
    if not m:
        return None
    dest = FILES / f"{slug}.xlsx"
    if dest.exists():
        return dest
    if offline:
        return None
    FILES.mkdir(parents=True, exist_ok=True)
    code = download(f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx", dest)
    if code == 200:
        return dest
    if code == 410:
        report.append((slug, f"old spreadsheet no longer exists: {url}"))
    else:
        report.append((slug, f"old spreadsheet is private. Open {url} signed in, "
                             f"File → Download → Microsoft Excel, save as `{dest}`, "
                             f"then rerun with `--force {slug}`"))
    return None


# ---------- writing ----------

def yaml_value(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(yaml_value(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


def render(meta, body):
    lines = ["---"]
    for k, v in meta.items():
        if v in (None, "", []) and k not in ("title",):
            continue
        lines.append(f"{k}: {yaml_value(v)}")
    lines.append("---")
    lines.append("")
    if body:
        lines.append("```{.song}")
        lines.extend(body)
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def load_hashes():
    if not HASHES.exists():
        return {}
    return {r["slug"]: r["sha256"] for r in csv.DictReader(HASHES.open())}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use data/raw/ only")
    ap.add_argument("--force", action="append", default=[], metavar="SLUG",
                    help="overwrite this song even if edited by hand")
    args = ap.parse_args()

    rows = list(csv.DictReader(open("data/songs.csv", newline="")))
    hashes = load_hashes()
    report, used = [], {}
    written = skipped = 0
    SONGS.mkdir(exist_ok=True)

    for row in rows:
        sheet_title = row["sheet_title"].strip()
        doc_text = fetch_doc(row["doc_id"], args.offline) if row["doc_id"] else None
        base = slugify(deinvert(sheet_title))
        used[base] = used.get(base, 0) + 1
        slug = base if used[base] == 1 else f"{base}-{used[base]}"
        r = []

        info = parse_doc(doc_text, slug, r) if doc_text else None
        if row["doc_id"] and not doc_text:
            r.append((slug, "Google Doc could not be downloaded (private?); page has no song text"))

        # Title: the Doc's title line when it extends the sheet title.
        title = deinvert(sheet_title)
        artist = deinvert(row["artist"]).strip()
        if info:
            doc_title, _, doc_artist = info["doc_title"].partition(" - ")
            doc_title = straight_quotes(doc_title).strip()
            if norm(doc_title).startswith(norm(sheet_title)) and len(doc_title) > len(title) + 2 \
                    and not re.search(r"\bby\b", doc_title):
                title = doc_title
            if row["source"] == "site" and doc_title:
                title = doc_title
            if not artist and doc_artist.strip():
                artist = straight_quotes(doc_artist).strip()
        if artist in ("?",):
            artist = ""

        # Key: the Doc's 'Key of' line, else the sheet, else the first chord.
        sheet_keys = [k for k in (key_name(x) for x in re.split(r"[\n,/]+", row["key"])) if k]
        key = (info and info["key"]) or (sheet_keys[0] if sheet_keys else None)
        alt_keys = list(dict.fromkeys((info["alt_keys"] if info else []) + sheet_keys[1:]))
        if not key and info:
            key = key_name(first_chord(info["body"]) or "")
            if key:
                r.append((slug, f"no key written; key set to the first chord, {key}"))
        alt_keys = [k for k in alt_keys if k != key]

        files, other_links = [], []
        for url in row["other_links"].split():
            if "spreadsheet" in url:
                got = fetch_spreadsheet(url, slug, args.offline, r)
                if got:
                    files.append(str(got.relative_to(SONGS)))
                    continue
            other_links.append(url)

        meta = {
            "title": title,
            "sort_title": invert(title),
            "artist": artist,
            "key": key,
            "alt_keys": alt_keys,
            "key_note": info["key_note"] if info else None,
            "youtube": info["youtube"] if info else None,
            "libraries": row["libraries"].split(),
            "difficulty": number(row["difficulty"]),
            "practice": number(row["practice"]),
            "fun": number(row["fun"]),
            "skill": number(row["skill"]),
            "poppy": number(row["poppy"]),
            "happy": number(row["happy"]),
            "spiritual": number(row["spiritual"]),
            "protest": number(row["protest"]),
            "voice_low": voice(row["low"], r, slug),
            "voice_high": voice(row["high"], r, slug),
            "added": row["added"] or None,
            "pages": number(row["pages"]),
            "source_doc": f"https://docs.google.com/document/d/{row['doc_id']}/edit" if row["doc_id"] else None,
            "other_links": other_links,
            "files": files,
        }
        if not info:
            r.append((slug, "no Google Doc; page has the sheet's details and links only"))
        text = render(meta, info["body"] if info else [])

        path = SONGS / f"{slug}.qmd"
        if path.exists() and slug not in args.force:
            current = sha(path.read_text())
            if slug not in hashes or current != hashes[slug]:
                skipped += 1
                continue  # edited by hand since the import; leave it
        path.write_text(text)
        hashes[slug] = sha(text)
        written += 1
        report.extend(r)

    with HASHES.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slug", "sha256"])
        for k in sorted(hashes):
            w.writerow([k, hashes[k]])

    lines = ["# Import report", "",
             "Generated by `_scripts/import_docs.py`. One line per thing to check by hand.", ""]
    for slug in sorted({s for s, _ in report}):
        lines.append(f"## [{slug}](../songs/{slug}.qmd)")
        lines.append("")
        lines.extend(f"- {msg}" for s, msg in report if s == slug)
        lines.append("")
    REPORT.write_text("\n".join(lines))
    print(f"{written} songs written, {skipped} left alone (edited by hand), "
          f"{len(report)} report lines -> {REPORT}")


if __name__ == "__main__":
    main()
