#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
archive="$project_root/artifacts/cgba_reproducibility_bundle.tar.gz"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT

cd "$project_root/artifacts"
sha256sum -c cgba_reproducibility_bundle.tar.gz.sha256
tar -xzf "$archive" -C "$temporary"
extracted="$temporary/$(basename "$project_root")"
cd "$extracted"
"$python_bin" reproduction/verify_method_lock.py
"$python_bin" -m pytest -q
"$python_bin" scripts/analyze_confirmation.py
"$python_bin" scripts/render_paper_assets.py
