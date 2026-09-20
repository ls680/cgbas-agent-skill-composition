#!/usr/bin/env bash
set -euo pipefail

: "${SCIENCEWORLD_JAR_SOURCE:?Set SCIENCEWORLD_JAR_SOURCE to the audited ScienceWorld JAR}"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${PYTHON_BIN:-python3}"
workspace_root="$(dirname "$project_root")"
vendor="$project_root/reproduction/vendor"
paper1="$workspace_root/01_skilllineage"
paper6="$workspace_root/06_rely_guarantee_diagnosis"
expected_jar_sha="e77b0fee7d68abe3ca5b12e57d86e2bfe7603f20c5200da0b0f085939faeb465"

actual_jar_sha="$(sha256sum "$SCIENCEWORLD_JAR_SOURCE" | cut -d' ' -f1)"
if [[ "$actual_jar_sha" != "$expected_jar_sha" ]]; then
  echo "ScienceWorld JAR hash mismatch" >&2
  exit 1
fi

mkdir -p "$paper1/src/skilllineage" \
  "$paper1/revisions/04_state_matched_execution" \
  "$paper1/research/validation/vendor" \
  "$paper6/src/mrgd" "$paper6/scripts"
cp -a "$vendor/01_skilllineage/src/skilllineage/." "$paper1/src/skilllineage/"
cp -a "$vendor/01_skilllineage/revisions/04_state_matched_execution/." \
  "$paper1/revisions/04_state_matched_execution/"
cp -a "$vendor/06_rely_guarantee_diagnosis/src/mrgd/." "$paper6/src/mrgd/"
cp -a "$vendor/06_rely_guarantee_diagnosis/scripts/." "$paper6/scripts/"
cp "$SCIENCEWORLD_JAR_SOURCE" \
  "$paper1/research/validation/vendor/scienceworld-e8216d6.jar"

"$python_bin" "$project_root/reproduction/verify_method_lock.py"
