#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project_name="$(basename "$project_root")"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
archive_name="cgba_reproducibility_bundle.tar.gz"

tar \
  --sort=name \
  --mtime='2026-09-09 00:00:00Z' \
  --owner=0 --group=0 --numeric-owner \
  --exclude="$project_name/.pytest_cache" \
  --exclude="$project_name/**/__pycache__" \
  --exclude="$project_name/paper/**/*.aux" \
  --exclude="$project_name/paper/**/*.bbl" \
  --exclude="$project_name/paper/**/*.blg" \
  --exclude="$project_name/paper/**/*.fdb_latexmk" \
  --exclude="$project_name/paper/**/*.fls" \
  --exclude="$project_name/paper/**/*.log" \
  --exclude="$project_name/paper/**/*.out" \
  --exclude="$project_name/paper/**/*.xdv" \
  --exclude="$project_name/artifacts/*" \
  -czf "$temporary/$archive_name" \
  -C "$(dirname "$project_root")" "$project_name"

mkdir -p "$project_root/artifacts"
mv "$temporary/$archive_name" "$project_root/artifacts/$archive_name"
cd "$project_root/artifacts"
sha256sum "$archive_name" > "$archive_name.sha256"
cat "$archive_name.sha256"
