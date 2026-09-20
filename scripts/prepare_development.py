#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT.parent / "06_rely_guarantee_diagnosis"


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(path: Path, values: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n")


def main() -> None:
    public_path = SOURCE / "data/confirmation/public_compositions.jsonl"
    label_path = SOURCE / "results/confirmation/final/labeled_records.jsonl"
    public = rows(public_path)
    labels = {row["spec_id"]: row for row in rows(label_path) if row["label"]["valid"]}
    healthy_by_task = {
        (row["environment"], labels[row["composition_id"]]["task_id"]): row["calls"]
        for row in public
        if row["composition_id"] in labels
        and labels[row["composition_id"]]["label"]["class"] == "no_conflict"
        and labels[row["composition_id"]]["candidate_success"]
    }
    incidents, outcomes = [], []
    for row in public:
        label = labels.get(row["composition_id"])
        if not label:
            continue
        key = row["environment"], label["task_id"]
        witness_calls = healthy_by_task.get(key)
        if not witness_calls:
            continue
        incidents.append({
            **row,
            "task_id": label["task_id"],
            "witness_calls": witness_calls,
            "information_boundary": [
                "public objective", "candidate calls", "MRGD-compatible contracts",
                "provenance-linked successful witness calls",
            ],
        })
        outcomes.append({
            "composition_id": row["composition_id"],
            "task_id": label["task_id"],
            "environment": label["environment"],
            "family": label["family"],
            "label": label["label"],
            "candidate_success": label["candidate_success"],
            "matched_correction_success": label["repair_success"],
        })
    write_rows(PROJECT / "data/development/public_incidents.jsonl", incidents)
    write_rows(PROJECT / "data/development/labels.jsonl", outcomes)
    manifest = {
        "status": "paper06_exposed_evidence_partitioned_for_paper13_development",
        "incidents": len(incidents),
        "tasks": len({row["task_id"] for row in incidents}),
        "classes": dict(Counter(row["label"]["class"] for row in outcomes)),
        "environments": dict(Counter(row["environment"] for row in outcomes)),
        "matched_correction_programs_copied": False,
        "source_sha256": {
            "public_compositions": digest(public_path),
            "causal_labels": digest(label_path),
            "preparer": digest(Path(__file__)),
        },
    }
    output = PROJECT / "data/development/manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
