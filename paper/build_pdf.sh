#!/usr/bin/env bash
# Build paper.pdf from paper.md (local preview; JOSS builds its own PDF from paper.md).
# Needs pandoc and a TeX Live with xelatex (e.g. TinyTeX), plus the DejaVu fonts.
set -euo pipefail
cd "$(dirname "$0")"
name="${1:-paper}"
export PATH="$HOME/.TinyTeX/bin/x86_64-linux:$PATH"
meta="$(mktemp --suffix=.yaml)"
trap 'rm -f "$meta"' EXIT
cat > "$meta" <<'YAML'
author: "Jonathan Sobel (ORCID 0000-0002-5111-4070) `\\\\`{=latex} Division of Infection Prevention and Control `\\\\`{=latex} University Hospital of Geneva (HUG), Geneva, Switzerland"
YAML
pandoc "$name.md" --metadata-file="$meta" --citeproc --bibliography=paper.bib --pdf-engine=xelatex \
  -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" -V fontsize=10pt \
  -V geometry:margin=2.4cm -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  -o "$name.pdf"
echo "built $name.pdf ($(pdfinfo "$name.pdf" | awk '/Pages/{print $2}') pages)"
