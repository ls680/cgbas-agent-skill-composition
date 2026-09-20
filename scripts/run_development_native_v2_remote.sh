#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${CGBA_TMPDIR:-/root/autodl-tmp/tmp/cgba_development_v2}"
mkdir -p "$tmp_root"
export TMPDIR="$tmp_root" TMP="$tmp_root" TEMP="$tmp_root"
export ALFWORLD_DATA="${ALFWORLD_DATA:-/root/autodl-tmp/cache/alfworld}"
cd "$project_root"
/root/autodl-tmp/envs/skilllineage/bin/python scripts/run_development_native_v2.py
