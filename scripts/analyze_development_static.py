#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> None:
    predictions = {row["composition_id"]: row for row in rows(PROJECT / "results/development/static/adapters.jsonl")}
    labels = rows(PROJECT / "data/development/labels.jsonl")
    by_class = Counter()
    correct_by_class = Counter()
    synthesized_by_class = Counter()
    diagnosis_exact = 0
    locality_pass = 0
    unchanged_controls = 0
    inserted_actions_by_class: dict[str, list[int]] = {}
    errors = []
    for label in labels:
        expected = label["label"]
        prediction = predictions[label["composition_id"]]
        conflict = expected["class"]
        by_class[conflict] += 1
        inserted_actions_by_class.setdefault(conflict, [])
        if prediction["status"] != "synthesized":
            errors.append(f"abstained:{label['composition_id']}")
            continue
        diagnosed = prediction["diagnosis"]
        exact = diagnosed["conflict_class"] == conflict and diagnosed["boundary_index"] == expected["boundary"]
        diagnosis_exact += int(exact)
        correct_by_class[conflict] += int(exact)
        synthesized_by_class[conflict] += 1
        local = len(prediction["inserted_call_ids"]) <= 1 and prediction["original_call_ids_unchanged"]
        locality_pass += int(local)
        inserted_ids = set(prediction["inserted_call_ids"])
        inserted_actions_by_class[conflict].append(sum(
            len(call["actions"])
            for call in prediction["calls"]
            if call["call_id"] in inserted_ids
        ))
        if conflict == "no_conflict":
            unchanged_controls += int(not prediction["inserted_call_ids"] and not prediction["wrapped_original_call_ids"])
    summary = {
        "status": "static_development_analyzed",
        "records": len(labels),
        "diagnosis_exact_rate": diagnosis_exact / len(labels),
        "synthesis_rate": sum(synthesized_by_class.values()) / len(labels),
        "locality_rate": locality_pass / len(labels),
        "healthy_unchanged_rate": unchanged_controls / by_class["no_conflict"],
        "adapter_action_cost": {
            "mean": sum(
                value for values in inserted_actions_by_class.values() for value in values
            ) / len(labels),
            "maximum": max(
                value for values in inserted_actions_by_class.values() for value in values
            ),
            "by_class": {
                key: {
                    "mean": sum(values) / len(values),
                    "maximum": max(values),
                }
                for key, values in sorted(inserted_actions_by_class.items())
            },
        },
        "by_class": {
            key: {
                "n": by_class[key],
                "diagnosis_exact_rate": correct_by_class[key] / by_class[key],
                "synthesis_rate": synthesized_by_class[key] / by_class[key],
            }
            for key in sorted(by_class)
        },
        "errors": errors,
        "native_outcomes_used": False,
    }
    output = PROJECT / "results/development/static/summary.json"
    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
