#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
submission_dir="$project_root/submission/journal_of_systems_and_software"
paper_dir="$project_root/paper/journal_of_systems_and_software"
build_dir="$submission_dir/build"
mkdir -p "$build_dir"

(
  cd "$paper_dir"
  latexmk -xelatex -interaction=nonstopmode -halt-on-error \
    -outdir="$build_dir" main.tex
)
(
  cd "$submission_dir"
  latexmk -xelatex -interaction=nonstopmode -halt-on-error \
    -outdir=build jss_cover_letter.tex
)

cp "$build_dir/main.pdf" "$submission_dir/jss_main_manuscript.pdf"
cp "$build_dir/jss_cover_letter.pdf" "$submission_dir/jss_cover_letter.pdf"
cp "$submission_dir/HIGHLIGHTS.txt" "$submission_dir/jss_highlights.txt"

package="$submission_dir/jss_editable_source.zip"
rm -f "$package"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
mkdir -p "$temporary/jss_source/paper" "$temporary/jss_source/results/confirmation/final" \
  "$temporary/jss_source/research"
cp "$paper_dir"/*.tex "$paper_dir"/*.bib "$temporary/jss_source/paper/"
cp "$submission_dir/SUBMISSION_METADATA.md" "$submission_dir/JSS_PRE_SUBMISSION_BLOCKERS.md" \
  "$submission_dir/HIGHLIGHTS.txt" "$temporary/jss_source/"
cp "$project_root/results/confirmation/final/summary.json" \
  "$project_root/results/confirmation/final/arm_summary.csv" \
  "$temporary/jss_source/results/confirmation/final/"
cp "$project_root/research/CONFIRMATION_METHOD_LOCK.json" "$temporary/jss_source/research/"
(
  cd "$temporary"
  zip -q -X -r "$package" jss_source
)
sha256sum "$submission_dir/jss_main_manuscript.pdf" \
  "$submission_dir/jss_cover_letter.pdf" "$submission_dir/jss_editable_source.zip" \
  > "$submission_dir/jss_submission_checksums.sha256"
printf 'Built JSS package in %s\n' "$submission_dir"
