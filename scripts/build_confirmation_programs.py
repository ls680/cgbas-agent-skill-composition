#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from cgba.adapters import diagnose_chain, synthesize_adapter
from cgba.programs import build_pairwise_contract_program, pairwise_diagnose


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(label: str, programs: list[dict], public_path: Path) -> None:
    output = PROJECT / "results/confirmation/programs" / label
    output.mkdir(parents=True, exist_ok=True)
    program_path = output / "programs.jsonl"
    if program_path.exists():
        raise RuntimeError(f"Frozen confirmation programs already exist for {label}")
    program_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in programs))
    completion = {
        "status": "confirmation_programs_frozen_before_candidate_or_adapter_outcomes",
        "arm": label, "records": len(programs),
        "synthesized": sum(row["status"] == "synthesized" for row in programs),
        "hidden_labels_accessed": False, "native_outcomes_accessed": False,
        "public_incidents_sha256": digest(public_path),
        "programs_sha256": digest(program_path),
    }
    (output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


def main() -> None:
    lock_path = PROJECT / "research/CONFIRMATION_METHOD_LOCK.json"
    if json.loads(lock_path.read_text())["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Method lock is invalid")
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    incidents = rows(public_path)
    cgba, pairwise, no_repair, rollback = [], [], [], []
    for row in incidents:
        repair = synthesize_adapter(
            calls=row["calls"], objective=row["objective"],
            witness_calls=row["witness_calls"],
        )
        cgba.append({
            "composition_id": row["composition_id"], "task_id": row["task_id"],
            "environment": row["environment"], "family": row["family"],
            "status": "synthesized", **repair,
        })
        pairwise.append(build_pairwise_contract_program(row, pairwise_diagnose(row["calls"])))
        no_repair.append({
            "composition_id": row["composition_id"], "task_id": row["task_id"],
            "environment": row["environment"], "family": row["family"],
            "diagnosis": diagnose_chain(row["calls"]), "status": "unchanged",
            "calls": row["calls"],
            "actions": [action for call in row["calls"] for action in call["actions"]],
            "inserted_call_ids": [], "wrapped_original_call_ids": [],
            "original_call_ids_unchanged": True,
        })
        rollback.append({
            "composition_id": row["composition_id"], "task_id": row["task_id"],
            "environment": row["environment"], "family": row["family"],
            "diagnosis": {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []},
            "status": "whole_chain_replacement", "calls": row["witness_calls"],
            "actions": [action for call in row["witness_calls"] for action in call["actions"]],
            "inserted_call_ids": [call["call_id"] for call in row["witness_calls"]],
            "wrapped_original_call_ids": [call["call_id"] for call in row["calls"]],
            "original_call_ids_unchanged": False,
        })
    write("cgba", cgba, public_path)
    write("pairwise_contract", pairwise, public_path)
    write("no_repair", no_repair, public_path)
    write("whole_chain_rollback", rollback, public_path)


if __name__ == "__main__":
    main()
