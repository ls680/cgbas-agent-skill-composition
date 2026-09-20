#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "usage: $0 PROGRAMS OUTPUT ARM" >&2
  exit 2
fi
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${CGBA_TMPDIR:-/root/autodl-tmp/tmp/cgba_comparator_native}"
mkdir -p "$tmp_root"
export TMPDIR="$tmp_root" TMP="$tmp_root" TEMP="$tmp_root"
export ALFWORLD_DATA="${ALFWORLD_DATA:-/root/autodl-tmp/cache/alfworld}"
cd "$project_root"
/root/autodl-tmp/envs/skilllineage/bin/python scripts/run_programs_native.py \
  --programs "$1" --output "$2" --arm "$3"
