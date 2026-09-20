#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from cgba.programs import build_pairwise_contract_program, pairwise_diagnose


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    public_path = PROJECT / "data/development/public_incidents.jsonl"
    incidents = rows(public_path)
    programs = [build_pairwise_contract_program(row, pairwise_diagnose(row["calls"])) for row in incidents]
    write_programs(
        label="pairwise_contract", programs=programs, public_path=public_path,
        metadata={
            "comparator": "pairwise_contract_without_provenance_or_global_liveness",
            "synthesized": sum(row["status"] == "synthesized" for row in programs),
        },
    )
    no_repair = [{
        "composition_id": row["composition_id"], "task_id": row["task_id"],
        "environment": row["environment"], "family": row["family"],
        "diagnosis": {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []},
        "status": "unchanged", "calls": row["calls"],
        "actions": [action for call in row["calls"] for action in call["actions"]],
        "inserted_call_ids": [], "wrapped_original_call_ids": [],
        "original_call_ids_unchanged": True,
    } for row in incidents]
    write_programs(
        label="no_repair", programs=no_repair, public_path=public_path,
        metadata={"comparator": "execute_candidate_without_repair"},
    )
    rollback = [{
        "composition_id": row["composition_id"], "task_id": row["task_id"],
        "environment": row["environment"], "family": row["family"],
        "diagnosis": {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []},
        "status": "whole_chain_replacement", "calls": row["witness_calls"],
        "actions": [action for call in row["witness_calls"] for action in call["actions"]],
        "inserted_call_ids": [call["call_id"] for call in row["witness_calls"]],
        "wrapped_original_call_ids": [call["call_id"] for call in row["calls"]],
        "original_call_ids_unchanged": False,
    } for row in incidents]
    write_programs(
        label="whole_chain_rollback", programs=rollback, public_path=public_path,
        metadata={"comparator": "replace_candidate_with_retained_successful_chain"},
    )


def write_programs(
    *, label: str, programs: list[dict], public_path: Path, metadata: dict
) -> None:
    output_dir = PROJECT / "results/development/comparators" / label
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "programs.jsonl"
    output_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in programs))
    manifest = {
        "status": "completed",
        **metadata,
        "records": len(programs),
        "public_incidents_sha256": digest(public_path),
        "programs_sha256": digest(output_path),
        "hidden_labels_accessed": False,
        "native_outcomes_accessed": False,
    }
    (output_dir / "completion.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
