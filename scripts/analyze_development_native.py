#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from cgba.runtime import native_action_accepted


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def summarize(values: list[dict]) -> dict:
    return {
        "n": len(values),
        "native_success_rate": sum(row["native_success"] for row in values) / len(values),
        "constrained_success_rate": sum(row["constrained_success"] for row in values) / len(values),
        "adapter_command_support_rate": sum(row["unsupported_adapter_commands"] == 0 for row in values) / len(values),
        "initial_state_match_rate": sum(row["initial_state_match"] for row in values) / len(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--programs", type=Path,
        default=PROJECT / "results/development/static/adapters.jsonl",
    )
    parser.add_argument("--arm", default="cgba")
    args = parser.parse_args()
    labels = {row["composition_id"]: row for row in rows(PROJECT / "data/development/labels.jsonl")}
    incidents = {
        row["composition_id"]: row
        for row in rows(PROJECT / "data/development/public_incidents.jsonl")
    }
    programs = {row["composition_id"]: row for row in rows(args.programs)}
    native = rows(args.native / "outcomes.jsonl")
    evaluated = []
    for row in native:
        label = labels[row["composition_id"]]
        program = programs[row["composition_id"]]
        witness_actions = {
            action
            for call in incidents[row["composition_id"]]["witness_calls"]
            for action in call["actions"]
        }
        unsupported = sum(
            bool(turn.get("adapter_action", False))
            and turn["action"] not in witness_actions
            and not turn.get("native_action_accepted", native_action_accepted(
                environment=row["environment"],
                listed_admissible=turn["listed_admissible"],
                observation=turn["observation"],
            ))
            for turn in row["outcome"]["turns"]
        )
        local = (
            len(program.get("inserted_call_ids", [])) <= 1
            and program.get("original_call_ids_unchanged", False)
        )
        native_success = bool(row["outcome"]["success"])
        evaluated.append({
            "composition_id": row["composition_id"],
            "task_id": row["task_id"],
            "environment": row["environment"],
            "family": row["family"],
            "conflict_class": label["label"]["class"],
            "native_success": native_success,
            "constrained_success": native_success and unsupported == 0 and local,
            "candidate_success": bool(label["candidate_success"]),
            "matched_correction_success": label["matched_correction_success"],
            "unsupported_adapter_commands": unsupported,
            "initial_state_match": bool(row["outcome"]["initial_state_match"]),
            "technical_error": row["outcome"]["technical_error"],
            "local": local,
            "wrapper_skips": len(row["outcome"].get("wrapper_events", [])),
        })
    causal = [row for row in evaluated if row["conflict_class"] != "no_conflict"]
    controls = [row for row in evaluated if row["conflict_class"] == "no_conflict"]
    by_class = defaultdict(list)
    by_environment = defaultdict(list)
    for row in evaluated:
        by_class[row["conflict_class"]].append(row)
        by_environment[row["environment"]].append(row)
    summary = {
        "status": "development_native_analyzed",
        "arm": args.arm,
        "programs": str(args.programs),
        "all": summarize(evaluated),
        "causal_conflicts": summarize(causal),
        "healthy_controls": summarize(controls),
        "no_repair_causal_success_rate": sum(row["candidate_success"] for row in causal) / len(causal),
        "matched_correction_causal_success_rate": sum(bool(row["matched_correction_success"]) for row in causal) / len(causal),
        "by_class": {key: summarize(value) for key, value in sorted(by_class.items())},
        "by_environment": {key: summarize(value) for key, value in sorted(by_environment.items())},
        "technical_errors": sum(bool(row["technical_error"]) for row in evaluated),
        "wrapper_skips": sum(row["wrapper_skips"] for row in evaluated),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evaluated.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in evaluated)
    )
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
