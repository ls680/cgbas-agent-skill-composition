#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time


PROJECT = Path(__file__).resolve().parents[1]
PAPER1 = PROJECT.parent / "01_skilllineage"
PAPER6 = PROJECT.parent / "06_rely_guarantee_diagnosis"
sys.path.insert(0, str(PROJECT / "src"))
from cgba.adapters import diagnose_chain
from cgba.runtime import (
    initial_runtime_state,
    native_action_accepted,
    proven_idempotent_skip,
    update_runtime_state,
)


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


def state_signature(observation: str, objective: str, actions: list[str]) -> str:
    return hashlib.sha256(json.dumps(
        {"observation": observation, "objective": objective, "actions": actions},
        ensure_ascii=False, sort_keys=True,
    ).encode()).hexdigest()


def execute(incident: dict, adapter: dict, record: dict, science, AlfworldEpisode) -> dict:
    started = time.perf_counter()
    episode = None
    turns, wrapper_events = [], []
    error = None
    score, done, initial_match = 0.0, False, False
    current_location = None
    opened: set[str] = set()
    boundary = adapter["diagnosis"]["boundary_index"]
    guarded_ids = set()
    if boundary is not None:
        guarded_ids = {
            call["call_id"] for call in incident["calls"][boundary:boundary + 2]
        }
    try:
        if incident["environment"] == "alfworld":
            episode = AlfworldEpisode(
                Path(os.environ["ALFWORLD_DATA"]) / incident["task_id"],
                max_steps=120, expert=False,
            )
        else:
            science.configure(incident["family"], record["variation"], "easy")
            episode = science
        observation, objective, admissible = episode.reset()
        initial_match = state_signature(observation, objective, admissible) == state_signature(
            record["observations"][0], record["task_description"],
            record["turns"][0]["admissible_actions"],
        )
        if not initial_match:
            raise RuntimeError("native replay initial state mismatch")
        current_location, opened = initial_runtime_state(observation)
        program_index = 0
        for call_index, call in enumerate(adapter["calls"]):
            for action in call["actions"]:
                if done:
                    break
                reason = proven_idempotent_skip(
                    action=action,
                    admissible_actions=admissible,
                    guarded=call["call_id"] in guarded_ids,
                    current_location=current_location,
                    opened=opened,
                )
                if reason:
                    wrapper_events.append({
                        "program_index": program_index,
                        "call_index": call_index,
                        "call_id": call["call_id"],
                        "action": action,
                        "reason": reason,
                    })
                    program_index += 1
                    continue
                next_observation, score, done, next_actions = episode.step(action)
                listed = action in admissible
                accepted = native_action_accepted(
                    environment=incident["environment"],
                    listed_admissible=listed,
                    observation=next_observation,
                )
                turns.append({
                    "program_index": program_index,
                    "call_index": call_index,
                    "call_id": call["call_id"],
                    "adapter_action": call["call_id"].startswith("adapter:"),
                    "action": action,
                    "listed_admissible": listed,
                    "native_action_accepted": accepted,
                    "observation": next_observation,
                    "score": score,
                    "done": done,
                })
                if accepted:
                    current_location, opened = update_runtime_state(
                        action=action, current_location=current_location, opened=opened
                    )
                observation, admissible = next_observation, next_actions
                program_index += 1
    except Exception as failure:
        error = f"{type(failure).__name__}: {failure}"
    finally:
        if incident["environment"] == "alfworld" and episode is not None:
            episode.close()
    return {
        "arm": "contract_guided_boundary_adapter_v2",
        "turns": turns,
        "wrapper_events": wrapper_events,
        "score": score,
        "done": done,
        "success": score >= 0.999,
        "initial_state_match": initial_match,
        "technical_error": error,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> None:
    public_path = PROJECT / "data/development/public_incidents.jsonl"
    adapter_path = PROJECT / "results/development/static/adapters.jsonl"
    oracle_path = PAPER6 / "data/confirmation/oracles/trajectories.jsonl"
    public = {row["composition_id"]: row for row in rows(public_path)}
    adapters = rows(adapter_path)
    oracles = {(row["environment"], row["task_id"]): row for row in rows(oracle_path)}
    executable = []
    for adapter in adapters:
        if adapter["status"] == "synthesized":
            executable.append(adapter)
            continue
        incident = public[adapter["composition_id"]]
        executable.append({
            **adapter,
            "diagnosis": diagnose_chain(incident["calls"]),
            "calls": incident["calls"],
            "actions": [action for call in incident["calls"] for action in call["actions"]],
            "inserted_call_ids": [],
            "wrapped_original_call_ids": [],
            "original_call_ids_unchanged": True,
        })
    adapters = executable
    sys.path.insert(0, str(PAPER1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(PAPER1 / "src"))
    from state_check import PinnedScienceworldSession
    from skilllineage.interactive_envs import AlfworldEpisode

    output_dir = PROJECT / "results/development_v2/native"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "outcomes.jsonl"
    run_spec = {
        "status": "paper13_development_v2_guarded_native_adapter_replay",
        "planned_compositions": [row["composition_id"] for row in adapters],
        "input_sha256": {
            "public_incidents": digest(public_path),
            "adapters": digest(adapter_path),
            "source_oracles": digest(oracle_path),
            "runner": digest(Path(__file__)),
            "runtime": digest(PROJECT / "src/cgba/runtime.py"),
        },
        "hidden_labels_accessed": False,
        "matched_correction_programs_accessed": False,
    }
    run_spec_path = output_dir / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Development v2 native inputs changed")
    if not run_spec_path.exists():
        if output_path.exists():
            raise RuntimeError("Unowned development v2 output")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(output_path)
    completed = {row["composition_id"] for row in saved}
    science = PinnedScienceworldSession(
        max_steps=160,
        jar=PAPER1 / "research/validation/vendor/scienceworld-e8216d6.jar",
    )
    try:
        for ordinal, adapter in enumerate(adapters, start=1):
            if adapter["composition_id"] in completed:
                continue
            incident = public[adapter["composition_id"]]
            outcome = execute(
                incident, adapter,
                oracles[(incident["environment"], incident["task_id"])],
                science, AlfworldEpisode,
            )
            result = {
                "composition_id": adapter["composition_id"],
                "task_id": incident["task_id"],
                "environment": incident["environment"],
                "family": incident["family"],
                "outcome": outcome,
            }
            append(output_path, result)
            completed.add(adapter["composition_id"])
            print(json.dumps({
                "progress": f"{ordinal}/{len(adapters)}",
                "environment": incident["environment"],
                "diagnosis": adapter["diagnosis"]["conflict_class"],
                "success": outcome["success"],
                "invalid_actions": sum(not turn["native_action_accepted"] for turn in outcome["turns"]),
                "wrapper_skips": len(outcome["wrapper_events"]),
                "error": outcome["technical_error"],
            }), flush=True)
    finally:
        science.close()
    outcomes = rows(output_path)
    if len(outcomes) != len(adapters):
        raise RuntimeError("Development v2 native run incomplete")
    completion = {
        "status": "completed" if not any(row["outcome"]["technical_error"] for row in outcomes) else "completed_with_technical_errors",
        "compositions": len(outcomes),
        "native_successes": sum(row["outcome"]["success"] for row in outcomes),
        "technical_errors": sum(bool(row["outcome"]["technical_error"]) for row in outcomes),
        "initial_state_matches": sum(row["outcome"]["initial_state_match"] for row in outcomes),
        "invalid_actions": sum(not turn["native_action_accepted"] for row in outcomes for turn in row["outcome"]["turns"]),
        "wrapper_skips": sum(len(row["outcome"]["wrapper_events"]) for row in outcomes),
        "by_environment": dict(Counter(row["environment"] for row in outcomes)),
        "outcomes_sha256": digest(output_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
