#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
PAPER1 = PROJECT.parent / "01_skilllineage"
sys.path.insert(0, str(PROJECT / "scripts"))
from run_programs_native import append, execute, rows


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--programs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    args = parser.parse_args()
    config_path = PROJECT / "configs/confirmation.json"
    config = json.loads(config_path.read_text())
    lock_path = PROJECT / config["paths"]["method_lock"]
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    oracle_path = PROJECT / config["paths"]["oracles"] / "trajectories.jsonl"
    causal_path = PROJECT / "data/confirmation/causal_native/outcomes.jsonl"
    programs = rows(args.programs)
    public = {row["composition_id"]: row for row in rows(public_path)}
    oracles = {(row["environment"], row["task_id"]): row for row in rows(oracle_path)}
    if {row["composition_id"] for row in programs} != set(public):
        raise RuntimeError("Program roster differs from confirmation public roster")
    sys.path.insert(0, str(PAPER1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(PAPER1 / "src"))
    from state_check import PinnedScienceworldSession
    from skilllineage.interactive_envs import AlfworldEpisode

    args.output.mkdir(parents=True, exist_ok=True)
    output_path = args.output / "outcomes.jsonl"
    run_spec = {
        "status": "paper13_independent_confirmation_program_native",
        "arm": args.arm, "records": len(programs),
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "programs": digest(args.programs), "public_incidents": digest(public_path),
            "source_oracles": digest(oracle_path), "causal_outcomes": digest(causal_path),
            "runner": digest(Path(__file__)),
            "shared_executor": digest(PROJECT / "scripts/run_programs_native.py"),
            "runtime": digest(PROJECT / "src/cgba/runtime.py"),
        },
    }
    run_spec_path = args.output / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Confirmation program inputs changed")
    if not run_spec_path.exists():
        if output_path.exists():
            raise RuntimeError("Unowned program native output")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(output_path)
    completed = {row["composition_id"] for row in saved}
    science = PinnedScienceworldSession(
        max_steps=config["max_steps"]["scienceworld"],
        jar=(PROJECT / config["paths"]["scienceworld_jar"]).resolve(),
    )
    try:
        for ordinal, program in enumerate(programs, start=1):
            composition_id = program["composition_id"]
            if composition_id in completed:
                continue
            incident = public[composition_id]
            outcome = execute(
                program, incident, oracles[(incident["environment"], incident["task_id"])],
                science, AlfworldEpisode, args.arm,
            )
            append(output_path, {
                "composition_id": composition_id, "task_id": incident["task_id"],
                "environment": incident["environment"], "family": incident["family"],
                "program_status": program["status"],
                "original_call_ids_unchanged": program["original_call_ids_unchanged"],
                "inserted_call_ids": program["inserted_call_ids"],
                "wrapped_original_call_ids": program["wrapped_original_call_ids"],
                "outcome": outcome,
            })
            completed.add(composition_id)
            print(json.dumps({
                "progress": f"{ordinal}/{len(programs)}", "arm": args.arm,
                "environment": incident["environment"], "success": outcome["success"],
                "unsupported_adapter_commands": sum(
                    not turn["adapter_command_supported"] for turn in outcome["turns"]
                ), "technical_error": outcome["technical_error"],
            }), flush=True)
    finally:
        science.close()
    outcomes = rows(output_path)
    if len(outcomes) != len(programs):
        raise RuntimeError("Confirmation program run incomplete")
    completion = {
        "status": "completed" if not any(row["outcome"]["technical_error"] for row in outcomes) else "completed_with_technical_errors",
        "arm": args.arm, "compositions": len(outcomes),
        "native_successes": sum(row["outcome"]["success"] for row in outcomes),
        "technical_errors": sum(bool(row["outcome"]["technical_error"]) for row in outcomes),
        "initial_state_matches": sum(row["outcome"]["initial_state_match"] for row in outcomes),
        "unsupported_adapter_commands": sum(
            not turn["adapter_command_supported"]
            for row in outcomes for turn in row["outcome"]["turns"]
        ),
        "by_environment": dict(Counter(row["environment"] for row in outcomes)),
        "outcomes_sha256": digest(output_path),
    }
    (args.output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
