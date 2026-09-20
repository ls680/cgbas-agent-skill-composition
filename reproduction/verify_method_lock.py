#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    lock_path = PROJECT / "research/CONFIRMATION_METHOD_LOCK.json"
    lock = json.loads(lock_path.read_text())
    mismatches = []
    external_files_not_present = []
    for relative, expected in lock["file_sha256"].items():
        path = PROJECT / relative
        if not path.exists() and relative.startswith("../"):
            external_files_not_present.append(relative)
            continue
        if not path.exists():
            mismatches.append({"path": relative, "expected": expected, "actual": "missing"})
            continue
        actual = digest(path)
        if actual != expected:
            mismatches.append({"path": relative, "expected": expected, "actual": actual})
    prior = digest(PROJECT / "data/confirmation/prior_exclusions.json")
    if prior != lock["prior_exclusions_sha256"]:
        mismatches.append({
            "path": "data/confirmation/prior_exclusions.json",
            "expected": lock["prior_exclusions_sha256"], "actual": prior,
        })
    result = {
        "status": "passed" if not mismatches else "failed",
        "locked_files": len(lock["file_sha256"]),
        "mismatches": mismatches,
        "external_files_not_present": external_files_not_present,
        "external_note": (
            "External dependency hashes remain recorded in the lock. Install them "
            "at the documented sibling paths before a full native rerun."
            if external_files_not_present else None
        ),
        "lock_sha256": digest(lock_path),
    }
    print(json.dumps(result, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
