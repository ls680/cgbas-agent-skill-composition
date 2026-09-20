#!/usr/bin/env bash
set -euo pipefail

paper_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for language in en zh; do
  cd "$paper_root/$language"
  latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
done
