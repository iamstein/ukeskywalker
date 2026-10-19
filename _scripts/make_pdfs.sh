#!/bin/sh
# Print each rendered song sheet (any libraries/*.qmd with `songbook:` in its
# front matter) to two PDFs next to its HTML page, one with chords and one
# with lyrics only, for the page's download buttons. Run after
# `quarto render`; the publish workflow does this.
set -e
cd "$(dirname "$0")/.."

for chrome in "$CHROME" google-chrome chromium \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
  if [ -n "$chrome" ] && command -v "$chrome" >/dev/null 2>&1; then break; fi
  chrome=""
done
if [ -z "$chrome" ]; then echo "make_pdfs: Chrome not found; set CHROME" >&2; exit 1; fi

for qmd in $(grep -l '^songbook:' libraries/*.qmd); do
  page="docs/${qmd%.qmd}"
  "$chrome" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf="$page.pdf" "file://$PWD/$page.html" 2>/dev/null
  "$chrome" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
    --print-to-pdf="$page-lyrics.pdf" "file://$PWD/$page.html?chords=off" 2>/dev/null
  echo "make_pdfs: $page.pdf, $page-lyrics.pdf"
done
