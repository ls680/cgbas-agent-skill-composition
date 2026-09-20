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


def main() -> None:
    config_path = PROJECT / "configs/confirmation.json"
    config = json.loads(config_path.read_text())
    paths = config["paths"]
    lock_path = PROJECT / paths["method_lock"]
    roster_path = PROJECT / paths["roster"]
    lock = json.loads(lock_path.read_text())
    roster = json.loads(roster_path.read_text())
    if lock["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Confirmation method lock is invalid")
    if roster["status"] != "content_blind_zero_overlap_roster_frozen_before_source_outcomes":
        raise RuntimeError("Confirmation roster is invalid")
    sys.path.insert(0, str(PAPER1 / "revisions/04_state_matched_execution"))
    sys.path.insert(0, str(PAPER1 / "src"))
    from state_check import PinnedScienceworldSession, validate_jar
    from skilllineage.interactive_envs import AlfworldEpisode

    jar = (PROJECT / paths["scienceworld_jar"]).resolve()
    validate_jar(jar)
    data_root = Path(os.environ["ALFWORLD_DATA"])
    output = PROJECT / paths["oracles"]
    output.mkdir(parents=True, exist_ok=True)
    run_spec = {
        "status": "paper13_independent_confirmation_source_oracles",
        "tasks": [
            {
                **task,
                **({"gamefile_sha256": digest(data_root / task["task_id"])} if task["environment"] == "alfworld" else {}),
            }
            for task in roster["tasks"]
        ],
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "roster": digest(roster_path), "collector": digest(Path(__file__)),
            "runtime": digest(PAPER1 / "src/skilllineage/interactive_envs.py"),
            "state_check": digest(PAPER1 / "revisions/04_state_matched_execution/state_check.py"),
            "scienceworld_jar": digest(jar),
        },
    }
    run_spec_path = output / "run_spec.json"
    trajectory_path = output / "trajectories.jsonl"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Confirmation oracle inputs changed")
    if not run_spec_path.exists():
        if trajectory_path.exists():
            raise RuntimeError("Unowned confirmation oracle output")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(trajectory_path)
    completed = {(row["environment"], row["task_id"]) for row in saved}
    expected = {(row["environment"], row["task_id"]) for row in roster["tasks"]}
    if len(saved) != len(completed) or not completed <= expected:
        raise RuntimeError("Invalid saved oracle records")
    science = PinnedScienceworldSession(max_steps=config["max_steps"]["scienceworld"], jar=jar)
    try:
        for ordinal, task in enumerate(roster["tasks"], start=1):
            key = task["environment"], task["task_id"]
            if key in completed:
                continue
            started, episode = time.perf_counter(), None
            actions, turns, observations = [], [], []
            objective, score, done, error = "", 0.0, False, None
            try:
                if task["environment"] == "alfworld":
                    episode = AlfworldEpisode(
                        data_root / task["task_id"],
                        max_steps=config["max_steps"]["alfworld"], expert=True,
                    )
                else:
                    science.env.load(task["family"], task["variation"], "easy", generateGoldPath=True)
                    if task["variation"] not in list(science.env.get_variations_test()):
                        raise ValueError("ScienceWorld variation is not official TEST")
                    episode = science
                observation, objective, admissible = episode.reset()
                observations.append(observation)
                gold = list(science.env.get_gold_action_sequence()) if task["environment"] == "scienceworld" else None
                for index in range(config["max_steps"][task["environment"]]):
                    action = episode.expert_action() if task["environment"] == "alfworld" else (
                        gold[index] if index < len(gold) else None
                    )
                    if not action:
                        error = "expert/gold actions exhausted before success"
                        break
                    next_observation, score, done, next_actions = episode.step(action)
                    turns.append({
                        "turn": index, "action": action,
                        "admissible_actions": admissible,
                        "listed_admissible": action in admissible,
                        "observation": next_observation, "score": score, "done": done,
                    })
                    actions.append(action)
                    observations.append(next_observation)
                    observation, admissible = next_observation, next_actions
                    if done:
                        break
                if score < 0.999:
                    error = error or "reference did not reach success"
            except Exception as failure:
                error = f"{type(failure).__name__}: {failure}"
            finally:
                if task["environment"] == "alfworld" and episode is not None:
                    episode.close()
            record = {
                **task, "split": "paper13_independent_confirmation",
                "task_description": objective, "executed_actions": actions,
                "observations": observations, "turns": turns, "score": score,
                "success": score >= 0.999, "done": done, "error": error,
                "unlisted_reference_actions": sum(not row["listed_admissible"] for row in turns),
                "elapsed_seconds": time.perf_counter() - started,
            }
            append(trajectory_path, record)
            completed.add(key)
            print(json.dumps({
                "progress": f"{ordinal}/{len(roster['tasks'])}",
                "environment": task["environment"], "family": task["family"],
                "success": record["success"], "error": record["error"],
            }), flush=True)
    finally:
        science.close()
    records = rows(trajectory_path)
    if {(row["environment"], row["task_id"]) for row in records} != expected:
        raise RuntimeError("Confirmation oracle collection incomplete")
    completion = {
        "status": "completed", "tasks": len(records),
        "successful_references": sum(row["success"] and not row["error"] for row in records),
        "failed_references": sum(not (row["success"] and not row["error"]) for row in records),
        "by_environment": dict(Counter(row["environment"] for row in records)),
        "trajectories_sha256": digest(trajectory_path),
    }
    (output / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
