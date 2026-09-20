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


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def state_signature(observation: str, objective: str, actions: list[str]) -> str:
    return hashlib.sha256(json.dumps(
        {"observation": observation, "objective": objective, "actions": actions},
        ensure_ascii=False,
        sort_keys=True,
    ).encode()).hexdigest()


def execute_arm(*, spec: dict, record: dict, actions: list[str], arm: str, science, alfworld_episode, max_steps: dict) -> dict:
    started = time.perf_counter()
    episode = None
    turns: list[dict] = []
    error = None
    score, done, initial_match = 0.0, False, False
    try:
        if spec["environment"] == "alfworld":
            episode = alfworld_episode(
                Path(os.environ["ALFWORLD_DATA"]) / spec["task_id"],
                max_steps=max_steps["alfworld"],
                expert=False,
            )
        else:
            science.configure(spec["family"], record["variation"], "easy")
            episode = science
        observation, objective, admissible = episode.reset()
        expected = state_signature(
            record["observations"][0],
            record["task_description"],
            record["turns"][0]["admissible_actions"],
        )
        initial_match = state_signature(observation, objective, admissible) == expected
        if not initial_match:
            raise RuntimeError("native replay initial state mismatch")
        for program_index, action in enumerate(actions):
            if done:
                break
            next_observation, score, done, next_actions = episode.step(action)
            turns.append({
                "program_index": program_index,
                "action": action,
                "listed_admissible": action in admissible,
                "observation": next_observation,
                "score": score,
                "done": done,
            })
            observation, admissible = next_observation, next_actions
    except Exception as failure:
        error = f"{type(failure).__name__}: {failure}"
    finally:
        if spec["environment"] == "alfworld" and episode is not None:
            episode.close()
    return {
        "arm": arm,
        "program": actions,
        "turns": turns,
        "score": score,
        "done": done,
        "success": score >= 0.999,
        "initial_state_match": initial_match,
        "technical_error": error,
        "elapsed_seconds": time.perf_counter() - started,
    }


def main() -> None:
    config_path = PROJECT / "configs/development.json"
    config = json.loads(config_path.read_text())
    source = (PROJECT / config["source_paper"]).resolve()
    paper1 = (PROJECT / config["paths"]["paper1_root"]).resolve()
    sys.path.insert(0, str(paper1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(paper1 / "src"))
    from state_check import PinnedScienceworldSession
    from skilllineage.interactive_envs import AlfworldEpisode

    oracle_path = source / config["source_oracles"]
    oracles = {
        (row["environment"], row["task_id"]): row
        for row in rows(oracle_path)
        if row["success"] and not row["error"]
    }
    spec_path = PROJECT / config["outputs"]["specs"]
    artifact = json.loads(spec_path.read_text())
    if artifact["status"] != "development_specs_from_exposed_evidence":
        raise RuntimeError("development specifications have unexpected status")

    output_dir = PROJECT / config["outputs"]["native"]
    output_dir.mkdir(parents=True, exist_ok=True)
    run_spec = {
        "status": "development_native_causal_replays",
        "planned_specs": [row["spec_id"] for row in artifact["specs"]],
        "planned_arms": sum(1 if row["intended_class"] == "no_conflict" else 2 for row in artifact["specs"]),
        "input_sha256": {
            "config": digest(config_path),
            "specs": digest(spec_path),
            "oracles": digest(oracle_path),
            "runner": digest(Path(__file__)),
            "contracts": digest(PROJECT / "src/mrgd/contracts.py"),
            "diagnoser": digest(PROJECT / "src/mrgd/diagnose.py"),
        },
    }
    run_spec_path = output_dir / "run_spec.json"
    outcome_path = output_dir / "outcomes.jsonl"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("development inputs changed after native outcomes began")
    if not run_spec_path.exists():
        if outcome_path.exists():
            raise RuntimeError("native outcome file exists without its run specification")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")

    saved = rows(outcome_path)
    completed = {row["spec_id"] for row in saved}
    if len(saved) != len(completed):
        raise RuntimeError("duplicate native outcomes")
    science = PinnedScienceworldSession(
        max_steps=config["max_steps"]["scienceworld"],
        jar=paper1 / config["paths"]["scienceworld_jar"],
    )
    try:
        for ordinal, spec in enumerate(artifact["specs"], start=1):
            if spec["spec_id"] in completed:
                continue
            record = oracles[(spec["environment"], spec["task_id"])]
            candidate = execute_arm(
                spec=spec,
                record=record,
                actions=spec["candidate_actions"],
                arm="candidate",
                science=science,
                alfworld_episode=AlfworldEpisode,
                max_steps=config["max_steps"],
            )
            repair = None
            if spec["intended_class"] != "no_conflict":
                repair = execute_arm(
                    spec=spec,
                    record=record,
                    actions=spec["repair_actions"],
                    arm="matched_correction",
                    science=science,
                    alfworld_episode=AlfworldEpisode,
                    max_steps=config["max_steps"],
                )
            outcome = {
                "spec_id": spec["spec_id"],
                "environment": spec["environment"],
                "family": spec["family"],
                "task_id": spec["task_id"],
                "intended_class": spec["intended_class"],
                "intended_boundary": spec["intended_boundary"],
                "source_oracle_success": True,
                "source_witnesses": spec["source_witnesses"],
                "candidate": candidate,
                "repair": repair,
            }
            append(outcome_path, outcome)
            completed.add(spec["spec_id"])
            print(json.dumps({
                "progress": f"{ordinal}/{len(artifact['specs'])}",
                "spec_id": spec["spec_id"],
                "environment": spec["environment"],
                "intended_class": spec["intended_class"],
                "candidate_success": candidate["success"],
                "repair_success": None if repair is None else repair["success"],
                "error": candidate["technical_error"] or (repair and repair["technical_error"]),
            }), flush=True)
    finally:
        science.close()

    outcomes = rows(outcome_path)
    if len(outcomes) != len(artifact["specs"]):
        raise RuntimeError("development native run incomplete")
    arms = [row["candidate"] for row in outcomes] + [
        row["repair"] for row in outcomes if row["repair"] is not None
    ]
    completion = {
        "status": "completed" if not any(arm["technical_error"] for arm in arms) else "completed_with_technical_errors",
        "specs": len(outcomes),
        "native_replays": len(arms),
        "candidate_failures": sum(not row["candidate"]["success"] for row in outcomes),
        "matched_correction_successes": sum(row["repair"] is not None and row["repair"]["success"] for row in outcomes),
        "technical_errors": sum(bool(arm["technical_error"]) for arm in arms),
        "initial_state_matches": sum(arm["initial_state_match"] for arm in arms),
        "by_environment": dict(Counter(row["environment"] for row in outcomes)),
        "by_intended_class": dict(Counter(row["intended_class"] for row in outcomes)),
        "outcomes_sha256": digest(outcome_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2), flush=True)


if __name__ == "__main__":
    main()
