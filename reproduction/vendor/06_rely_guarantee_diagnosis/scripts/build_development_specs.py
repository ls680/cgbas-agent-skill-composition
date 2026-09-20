#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from mrgd.actions import parse_action, role_name
from mrgd.contracts import compile_call, infer_roles, segment_trace, trace_hash


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def flatten(calls: list[dict]) -> list[str]:
    return [action for call in calls for action in call["actions"]]


def identifier(record: dict, conflict_class: str) -> str:
    value = f"{record['environment']}|{record['task_id']}|{conflict_class}"
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def alternate_color(target: str) -> str:
    colors = ["red", "green", "blue", "yellow", "orange", "purple"]
    found = re.search(r"\b(" + "|".join(colors) + r") box$", target)
    current = found.group(1) if found else "red"
    return colors[(colors.index(current) + 1) % len(colors)] + " box"


def make_clobber(record: dict, base: list[dict]) -> dict | None:
    roles = infer_roles(record["family"], record["executed_actions"])
    events = [parse_action(action) for action in record["executed_actions"]]
    acquired = [event for event in events if event.operator == "acquire" and event.subject != "thermometer"]
    final = next((event for event in reversed(events) if event.operator in {"place", "use"}), None)
    if not final or "holds:subject" not in base[-1]["contract"]["rely"]:
        return None
    if record["environment"] == "alfworld":
        if not acquired or not acquired[-1].target:
            return None
        source = acquired[-1].target
        actions = [f"go to {source}", f"move {acquired[-1].subject} to {source}"]
    else:
        raw = list(base[-1]["actions"])
        if final.operator != "place":
            return None
        replacement = alternate_color(final.target)
        actions = [
            re.sub(r"to (?:red|green|blue|yellow|orange|purple) box$", f"to {replacement}", action)
            if index == len(raw) - 1 else action
            for index, action in enumerate(raw)
        ]
    witness = trace_hash(record)
    call = compile_call(
        call_id=f"{witness[:12]}:clobber",
        actions=actions,
        family=record["family"],
        roles=roles,
        witness=witness,
        schema_witness=witness,
        goal_terminal=False,
    )
    call["contract"]["bindings"].pop("destination", None)
    call["contract"]["guarantee"] = [
        value for value in call["contract"]["guarantee"] if value != "goal:complete"
    ]
    effect = parse_action(actions[-1])
    goal_destination = base[-1]["contract"]["bindings"].get("destination", "")
    call["contract"]["effect_guard"] = {
        "applicable": (
            record["environment"] == "alfworld"
            or bool(effect.target and role_name(effect.target) in record["task_description"].lower())
        ),
        "goal_satisfying": bool(
            effect.operator == "place"
            and goal_destination
            and role_name(effect.target) == role_name(goal_destination)
        ),
        "effect_destination": effect.target,
        "evidence": (
            "ALFWorld navigation-and-place schema"
            if record["environment"] == "alfworld"
            else "effect destination appears in public task description"
        ),
    }
    return call


def spec(record: dict, conflict_class: str, candidate: list[dict], repair: list[dict], boundary: int | None, extra: dict | None = None) -> dict:
    result = {
        "spec_id": identifier(record, conflict_class),
        "environment": record["environment"],
        "family": record["family"],
        "task_id": record["task_id"],
        "variation": record.get("variation"),
        "objective": record["task_description"],
        "intended_class": conflict_class,
        "intended_boundary": boundary,
        "candidate_calls": candidate,
        "repair_calls": repair,
        "candidate_actions": flatten(candidate),
        "repair_actions": flatten(repair),
        "source_witnesses": sorted({
            witness
            for call in candidate
            for witness in call["contract"]["witnesses"]
        }),
    }
    if extra:
        result.update(extra)
    return result


def main() -> None:
    config = json.loads((PROJECT / "configs/development.json").read_text())
    source = (PROJECT / config["source_paper"]).resolve()
    records = [row for row in rows(source / config["source_oracles"]) if row["success"] and not row["error"]]
    bases = {(row["environment"], row["task_id"]): segment_trace(row) for row in records}
    roles = {(row["environment"], row["task_id"]): infer_roles(row["family"], row["executed_actions"]) for row in records}

    donors: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        donors.setdefault((record["environment"], record["family"]), []).append(record)

    specs = []
    for record in records:
        key = record["environment"], record["task_id"]
        base = bases[key]
        if len(base) < 2:
            continue
        specs.append(spec(record, "no_conflict", base, base, None))

        witness = trace_hash(record)
        neutral_action = "look" if record["environment"] == "alfworld" else "look around"
        neutral = compile_call(
            call_id=f"{witness[:12]}:neutral",
            actions=[neutral_action],
            family=record["family"],
            roles=roles[key],
            witness=witness,
        )
        rely_candidate = [neutral, base[-1]]
        specs.append(spec(record, "rely_gap", rely_candidate, base, 0))

        clobber = make_clobber(record, base)
        if clobber is not None:
            inserted = len(base) - 1
            clobber_candidate = base[:-1] + [clobber, base[-1]]
            specs.append(spec(record, "clobber", clobber_candidate, base, inserted))

        current_subject = roles[key]["subject"]
        alternatives = [
            donor for donor in donors[(record["environment"], record["family"])]
            if donor["task_id"] != record["task_id"]
            and infer_roles(donor["family"], donor["executed_actions"])["subject"] != current_subject
        ]
        alternatives = [
            donor for donor in alternatives
            if "subject" in bases[(donor["environment"], donor["task_id"])][-1]["contract"]["bindings"]
        ]
        if alternatives:
            donor = min(alternatives, key=lambda row: hashlib.sha256(
                f"{config['generation_seed']}|{record['task_id']}|{row['task_id']}".encode()
            ).hexdigest())
            donor_call = bases[(donor["environment"], donor["task_id"])][-1]
            role_candidate = base[:-1] + [donor_call]
            specs.append(spec(record, "role_mismatch", role_candidate, base, len(role_candidate) - 2, {
                "donor_task_id": donor["task_id"],
            }))

        validation = compile_call(
            call_id=f"{witness[:12]}:local-validator",
            actions=[],
            family=record["family"],
            roles=roles[key],
            witness=witness,
            validation_claims=["holds:subject"],
            validation_scope="post-acquisition handoff",
        )
        validation["contract"]["rely"] = ["holds:subject"]
        if clobber is not None:
            prefix = base[:-1]
            validation_candidate = prefix + [validation, clobber, base[-1]]
            specs.append(spec(
                record,
                "stale_validation",
                validation_candidate,
                base,
                len(prefix),
            ))

    artifact = {
        "status": "development_specs_from_exposed_evidence",
        "native_outcomes_read_by_generator": False,
        "source_tasks": len(records),
        "spec_count": len(specs),
        "by_environment": dict(Counter(row["environment"] for row in specs)),
        "by_intended_class": dict(Counter(row["intended_class"] for row in specs)),
        "specs": specs,
    }
    output = PROJECT / config["outputs"]["specs"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps({key: artifact[key] for key in ("status", "source_tasks", "spec_count", "by_environment", "by_intended_class")}, indent=2))


if __name__ == "__main__":
    main()
