#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_root="${CGBA_TMPDIR:-/root/autodl-tmp/tmp/cgba_confirmation}"
mkdir -p "$tmp_root"
export TMPDIR="$tmp_root" TMP="$tmp_root" TEMP="$tmp_root"
export ALFWORLD_DATA="${ALFWORLD_DATA:-/root/autodl-tmp/cache/alfworld}"
export HF_HOME="${HF_HOME:-/root/autodl-tmp/cache/huggingface}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
cd "$project_root"
/root/autodl-tmp/envs/skilllineage/bin/python "$@"
