#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
output="$project_root/artifacts/cgba_journal_submission_source.zip"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
mkdir -p "$project_root/artifacts"
mkdir -p "$temporary/submission/paper/en" "$temporary/submission/paper/zh" \
  "$temporary/submission/results/confirmation/final"

required=(
  paper/en/main.tex
  paper/zh/main.tex
  paper/references.bib
  paper/results_macros.tex
  paper/HIGHLIGHTS.md
  paper/COVER_LETTER.md
  paper/STATEMENTS_AND_DECLARATIONS.md
  paper/SUBMISSION_METADATA.md
  results/confirmation/final/summary.json
  results/confirmation/final/arm_summary.csv
  research/CONFIRMATION_METHOD_LOCK.json
)
for relative in "${required[@]}"; do
  if [[ ! -s "$project_root/$relative" ]]; then
    echo "Missing required submission artifact: $relative" >&2
    exit 1
  fi
done

cp "$project_root/paper/en/main.tex" "$temporary/submission/paper/en/"
cp "$project_root/paper/zh/main.tex" "$temporary/submission/paper/zh/"
cp "$project_root/paper/references.bib" "$project_root/paper/results_macros.tex" \
  "$project_root/paper/"table_*.tex "$temporary/submission/paper/"
cp "$project_root/paper/"*.md "$temporary/submission/paper/"
cp "$project_root/results/confirmation/final/summary.json" \
  "$project_root/results/confirmation/final/arm_summary.csv" \
  "$temporary/submission/results/confirmation/final/"
cp "$project_root/research/CONFIRMATION_METHOD_LOCK.json" "$temporary/submission/"

for language in en zh; do
  (
    cd "$temporary/submission/paper/$language"
    latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
    if grep -Eq "There were undefined references|Citation .* undefined|Overfull \\\\hbox|Missing character:" main.log; then
      echo "Submission-source LaTeX verification failed for $language" >&2
      exit 1
    fi
    rm -f main.aux main.bbl main.blg main.fdb_latexmk main.fls main.log \
      main.out main.pdf main.xdv
  )
done

cd "$temporary"
zip -q -X -r "$output" submission
cd "$project_root/artifacts"
sha256sum "$(basename "$output")" > "$(basename "$output").sha256"
cat "$(basename "$output").sha256"
