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
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


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
        raise RuntimeError("Cannot load the frozen Paper 06 native executor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.execute_arm


def main() -> None:
    public_path = PROJECT / "data/development/public_incidents.jsonl"
    adapter_path = PROJECT / "results/development/static/adapters.jsonl"
    oracle_path = PAPER6 / "data/confirmation/oracles/trajectories.jsonl"
    public = {row["composition_id"]: row for row in rows(public_path)}
    adapters = [row for row in rows(adapter_path) if row["status"] == "synthesized"]
    oracles = {(row["environment"], row["task_id"]): row for row in rows(oracle_path)}
    execute_arm = load_execute_arm()

    sys.path.insert(0, str(PAPER1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(PAPER1 / "src"))
    from state_check import PinnedScienceworldSession
    from skilllineage.interactive_envs import AlfworldEpisode

    output_dir = PROJECT / "results/development/native"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "outcomes.jsonl"
    run_spec = {
        "status": "paper13_exposed_development_native_adapter_replay",
        "planned_compositions": [row["composition_id"] for row in adapters],
        "input_sha256": {
            "public_incidents": digest(public_path),
            "adapters": digest(adapter_path),
            "source_oracles": digest(oracle_path),
            "runner": digest(Path(__file__)),
            "paper06_executor": digest(PAPER6 / "scripts/run_development_native.py"),
        },
        "hidden_labels_accessed": False,
        "matched_correction_programs_accessed": False,
    }
    run_spec_path = output_dir / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Development native inputs changed")
    if not run_spec_path.exists():
        if output_path.exists():
            raise RuntimeError("Unowned native development output")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(output_path)
    completed = {row["composition_id"] for row in saved}
    if len(saved) != len(completed):
        raise RuntimeError("Duplicate native adapter outcomes")

    max_steps = {"alfworld": 120, "scienceworld": 160}
    science = PinnedScienceworldSession(
        max_steps=max_steps["scienceworld"],
        jar=PAPER1 / "research/validation/vendor/scienceworld-e8216d6.jar",
    )
    try:
        for ordinal, adapter in enumerate(adapters, start=1):
            composition_id = adapter["composition_id"]
            if composition_id in completed:
                continue
            incident = public[composition_id]
            record = oracles[(incident["environment"], incident["task_id"])]
            outcome = execute_arm(
                spec=incident,
                record=record,
                actions=adapter["actions"],
                arm="contract_guided_boundary_adapter",
                science=science,
                alfworld_episode=AlfworldEpisode,
                max_steps=max_steps,
            )
            result = {
                "composition_id": composition_id,
                "task_id": incident["task_id"],
                "environment": incident["environment"],
                "family": incident["family"],
                "diagnosis": adapter["diagnosis"],
                "inserted_call_ids": adapter["inserted_call_ids"],
                "wrapped_original_call_ids": adapter["wrapped_original_call_ids"],
                "original_call_ids_unchanged": adapter["original_call_ids_unchanged"],
                "outcome": outcome,
            }
            append(output_path, result)
            completed.add(composition_id)
            print(json.dumps({
                "progress": f"{ordinal}/{len(adapters)}",
                "environment": incident["environment"],
                "diagnosis": adapter["diagnosis"]["conflict_class"],
                "success": outcome["success"],
                "invalid_actions": sum(not turn["listed_admissible"] for turn in outcome["turns"]),
                "error": outcome["technical_error"],
            }), flush=True)
    finally:
        science.close()
    outcomes = rows(output_path)
    if len(outcomes) != len(adapters):
        raise RuntimeError("Development native adapter run incomplete")
    completion = {
        "status": "completed" if not any(row["outcome"]["technical_error"] for row in outcomes) else "completed_with_technical_errors",
        "compositions": len(outcomes),
        "native_successes": sum(row["outcome"]["success"] for row in outcomes),
        "technical_errors": sum(bool(row["outcome"]["technical_error"]) for row in outcomes),
        "initial_state_matches": sum(row["outcome"]["initial_state_match"] for row in outcomes),
        "invalid_actions": sum(not turn["listed_admissible"] for row in outcomes for turn in row["outcome"]["turns"]),
        "by_environment": dict(Counter(row["environment"] for row in outcomes)),
        "outcomes_sha256": digest(output_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
