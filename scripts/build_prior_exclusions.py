#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
EVIDENCE = (
    WORKSPACE / "01_skilllineage/revisions/23_reserved_confirmation/reserved_roster.json",
    WORKSPACE / "01_skilllineage/revisions/24_operator_transfer_confirmation/reserved_roster.json",
    WORKSPACE / "03_risk_limited_release/data/confirmation/roster.json",
    WORKSPACE / "03_risk_limited_release/data/confirmation/roster_pre_portability_revision.json",
    WORKSPACE / "04_state_guarded_repair/data/confirmation/roster.json",
    WORKSPACE / "05_witnessed_contracts/data/confirmation/roster.json",
    WORKSPACE / "12_counterfactual_library_growth/data/development/prior_exclusions.json",
    WORKSPACE / "12_counterfactual_library_growth/data/development/design.json",
    WORKSPACE / "12_counterfactual_library_growth/data/confirmation/design.json",
    WORKSPACE / "12_counterfactual_library_growth/data/confirmation/roster.json",
    PROJECT / "data/development/public_incidents.jsonl",
)
TASK_KEYS = {"task_id", "source_task_id", "target_task_id"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path: Path) -> list[object]:
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [json.loads(path.read_text())]


def collect(value: object, key: str | None = None) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key in TASK_KEYS and isinstance(child, str):
                found.add(child)
            elif child_key == "excluded_task_ids" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, str))
            else:
                found.update(collect(child, child_key))
    elif isinstance(value, list):
        for child in value:
            found.update(collect(child, key))
    return found


def main() -> None:
    excluded: set[str] = set()
    evidence = []
    for path in EVIDENCE:
        file_ids: set[str] = set()
        for record in records(path):
            file_ids.update(collect(record))
        excluded.update(file_ids)
        evidence.append({
            "path": str(path.relative_to(WORKSPACE)),
            "sha256": digest(path),
            "task_ids_found": len(file_ids),
        })
    output = {
        "status": "paper13_prior_task_exclusion_union_before_confirmation_selection",
        "selection_performed": False,
        "excluded_task_count": len(excluded),
        "alfworld_task_count": sum(value.startswith("json_2.1.1/") for value in excluded),
        "scienceworld_task_count": sum(not value.startswith("json_2.1.1/") for value in excluded),
        "evidence_files": evidence,
        "excluded_task_ids": sorted(excluded),
    }
    destination = PROJECT / "data/confirmation/prior_exclusions.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "excluded_task_ids"}, indent=2))


if __name__ == "__main__":
    main()
