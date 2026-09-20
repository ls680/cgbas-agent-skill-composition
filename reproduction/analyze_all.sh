#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
cd "$project_root"
"$python_bin" reproduction/verify_method_lock.py
"$python_bin" scripts/analyze_confirmation.py
"$python_bin" scripts/render_paper_assets.py
