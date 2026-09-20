#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank(task: dict, seed: str) -> str:
    key = f"{seed}|{task['environment']}|{task['family']}|{task['task_id']}"
    return hashlib.sha256(key.encode()).hexdigest()


def main() -> None:
    config_path = PROJECT / "configs/confirmation.json"
    config = json.loads(config_path.read_text())
    paths = config["paths"]
    lock_path = (PROJECT / paths["method_lock"]).resolve()
    exclusion_path = (PROJECT / paths["prior_exclusions"]).resolve()
    inventory_path = (PROJECT / paths["inventory"]).resolve()
    snapshot_path = (PROJECT / paths["reserved_snapshot"]).resolve()
    lock = json.loads(lock_path.read_text())
    if lock["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Development method and comparators are not frozen")
    exclusions = json.loads(exclusion_path.read_text())
    if exclusions["selection_performed"]:
        raise RuntimeError("Prior-exclusion artifact was created after selection")
    used = set(exclusions["excluded_task_ids"])
    inventory = json.loads(inventory_path.read_text())["tasks"]
    snapshot = json.loads(snapshot_path.read_text())["reserved_test_pool"]
    selected = []
    for family, quota in config["alfworld_tasks_by_family"].items():
        candidates = [
            task for task in inventory
            if task["environment"] == "alfworld"
            and task["family"] == family
            and task["official_split"] in config["alfworld_official_splits"]
            and task["compatible_with_original_scope"]
            and task["task_id"] not in used
        ]
        chosen = sorted(candidates, key=lambda task: rank(task, config["selection_seed"]))[:quota]
        if len(chosen) != quota:
            raise RuntimeError(f"Insufficient untouched ALFWorld tasks for {family}")
        selected.extend(chosen)
    for family, quota in config["scienceworld_tasks_by_family"].items():
        candidates = [
            task for task in snapshot
            if task["environment"] == "scienceworld"
            and task["family"] == family
            and task["compatible_with_original_scope"]
            and task["task_id"] not in used
        ]
        chosen = sorted(candidates, key=lambda task: rank(task, config["selection_seed"]))[:quota]
        if len(chosen) != quota:
            raise RuntimeError(f"Insufficient untouched ScienceWorld tasks for {family}")
        selected.extend(chosen)
    task_ids = [row["task_id"] for row in selected]
    if len(task_ids) != len(set(task_ids)) or set(task_ids) & used:
        raise RuntimeError("Confirmation roster is not unique and zero-overlap")
    artifact = {
        "status": "content_blind_zero_overlap_roster_frozen_before_source_outcomes",
        "selection_uses_only": [
            "environment", "family", "task_id", "official split",
            "compatibility flag", "prior-exposure exclusion", "salted SHA-256 rank",
        ],
        "selection_seed": config["selection_seed"],
        "task_count": len(selected),
        "by_environment": dict(Counter(row["environment"] for row in selected)),
        "by_environment_family": {
            "/".join(key): value
            for key, value in sorted(Counter(
                (row["environment"], row["family"]) for row in selected
            ).items())
        },
        "overlap_with_prior_tasks": 0,
        "tasks": selected,
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "prior_exclusions": digest(exclusion_path), "inventory": digest(inventory_path),
            "reserved_snapshot": digest(snapshot_path), "script": digest(Path(__file__)),
        },
    }
    output = PROJECT / paths["roster"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and json.loads(output.read_text()) != artifact:
        raise RuntimeError("Frozen confirmation roster changed")
    output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({
        "status": artifact["status"], "task_count": artifact["task_count"],
        "by_environment": artifact["by_environment"],
        "by_environment_family": artifact["by_environment_family"],
    }, indent=2))


if __name__ == "__main__":
    main()
