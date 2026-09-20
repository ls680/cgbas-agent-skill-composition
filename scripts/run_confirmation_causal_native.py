#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
PAPER1 = PROJECT.parent / "01_skilllineage"
PAPER6 = PROJECT.parent / "06_rely_guarantee_diagnosis"


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_execute_arm():
    source = PAPER6 / "scripts/run_development_native.py"
    spec = importlib.util.spec_from_file_location("paper06_native_executor", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load frozen Paper 06 native executor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_arm


def main() -> None:
    config_path = PROJECT / "configs/confirmation.json"
    config = json.loads(config_path.read_text())
    lock_path = PROJECT / config["paths"]["method_lock"]
    spec_path = PROJECT / "data/confirmation/specs.json"
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    oracle_path = PROJECT / config["paths"]["oracles"] / "trajectories.jsonl"
    if json.loads(lock_path.read_text())["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Method lock is invalid")
    artifact = json.loads(spec_path.read_text())
    if artifact["status"] != "confirmation_incidents_frozen_before_candidate_or_matched_outcomes":
        raise RuntimeError("Confirmation incidents are not frozen")
    specs = artifact["specs"]
    oracles = {(row["environment"], row["task_id"]): row for row in rows(oracle_path)}
    execute_arm = load_execute_arm()
    sys.path.insert(0, str(PAPER1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(PAPER1 / "src"))
    from state_check import PinnedScienceworldSession
    from skilllineage.interactive_envs import AlfworldEpisode

    output_dir = PROJECT / "data/confirmation/causal_native"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "outcomes.jsonl"
    frozen_programs = sorted((PROJECT / "results/confirmation").glob("**/programs.jsonl"))
    run_spec = {
        "status": "paper13_independent_confirmation_causal_native",
        "planned_specs": [row["spec_id"] for row in specs],
        "planned_replays": sum(1 if row["intended_class"] == "no_conflict" else 2 for row in specs),
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "specs": digest(spec_path), "public_incidents": digest(public_path),
            "source_oracles": digest(oracle_path), "runner": digest(Path(__file__)),
            "paper06_executor": digest(PAPER6 / "scripts/run_development_native.py"),
            **{
                f"frozen_program_{index}": digest(path)
                for index, path in enumerate(frozen_programs, start=1)
            },
        },
    }
    run_spec_path = output_dir / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Confirmation causal inputs changed")
    if not run_spec_path.exists():
        if output_path.exists():
            raise RuntimeError("Unowned causal native outcomes")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(output_path)
    completed = {row["spec_id"] for row in saved}
    science = PinnedScienceworldSession(
        max_steps=config["max_steps"]["scienceworld"],
        jar=(PROJECT / config["paths"]["scienceworld_jar"]).resolve(),
    )
    try:
        for ordinal, spec in enumerate(specs, start=1):
            if spec["spec_id"] in completed:
                continue
            record = oracles[(spec["environment"], spec["task_id"])]
            candidate = execute_arm(
                spec=spec, record=record, actions=spec["candidate_actions"], arm="candidate",
                science=science, alfworld_episode=AlfworldEpisode,
                max_steps=config["max_steps"],
            )
            correction = None
            if spec["intended_class"] != "no_conflict":
                correction = execute_arm(
                    spec=spec, record=record, actions=spec["repair_actions"],
                    arm="matched_correction", science=science,
                    alfworld_episode=AlfworldEpisode, max_steps=config["max_steps"],
                )
            append(output_path, {
                "spec_id": spec["spec_id"], "environment": spec["environment"],
                "family": spec["family"], "task_id": spec["task_id"],
                "intended_class": spec["intended_class"],
                "intended_boundary": spec["intended_boundary"],
                "source_oracle_success": True, "source_witnesses": spec["source_witnesses"],
                "candidate": candidate, "matched_correction": correction,
            })
            completed.add(spec["spec_id"])
            print(json.dumps({
                "progress": f"{ordinal}/{len(specs)}",
                "environment": spec["environment"],
                "intended_class": spec["intended_class"],
                "candidate_success": candidate["success"],
                "correction_success": None if correction is None else correction["success"],
                "technical_error": candidate["technical_error"] or (
                    correction and correction["technical_error"]
                ),
            }), flush=True)
    finally:
        science.close()
    outcomes = rows(output_path)
    if len(outcomes) != len(specs):
        raise RuntimeError("Causal confirmation run incomplete")
    arms = [row["candidate"] for row in outcomes] + [
        row["matched_correction"] for row in outcomes if row["matched_correction"] is not None
    ]
    completion = {
        "status": "completed" if not any(row["technical_error"] for row in arms) else "completed_with_technical_errors",
        "specs": len(outcomes), "native_replays": len(arms),
        "candidate_failures": sum(not row["candidate"]["success"] for row in outcomes),
        "matched_correction_successes": sum(
            row["matched_correction"] is not None and row["matched_correction"]["success"]
            for row in outcomes
        ),
        "technical_errors": sum(bool(row["technical_error"]) for row in arms),
        "initial_state_matches": sum(row["initial_state_match"] for row in arms),
        "by_environment": dict(Counter(row["environment"] for row in outcomes)),
        "by_intended_class": dict(Counter(row["intended_class"] for row in outcomes)),
        "outcomes_sha256": digest(output_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
