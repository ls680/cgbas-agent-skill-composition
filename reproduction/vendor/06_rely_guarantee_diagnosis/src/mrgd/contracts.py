from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .actions import Event, norm, parse_action, role_name


CRITICAL_OPERATORS = {"acquire", "focus", "clean", "cool", "heat", "measure", "place", "use"}


def trace_hash(record: dict) -> str:
    payload = {
        "environment": record["environment"],
        "task_id": record["task_id"],
        "objective": record["task_description"],
        "actions": record["executed_actions"],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def infer_roles(family: str, actions: list[str]) -> dict[str, str]:
    events = [parse_action(action) for action in actions]
    final = next((event for event in reversed(events) if event.operator in {"place", "use"}), Event("other"))
    acquired = [event.subject for event in events if event.operator == "acquire"]
    focused = [event.subject for event in events if event.operator == "focus" and "thermometer" not in event.subject]
    if final.operator == "place":
        subject = norm(final.subject)
        destination = norm(final.target)
    else:
        subject = acquired[-1] if acquired else (focused[-1] if focused else "")
        destination = norm(final.subject)
    if family in {"find-living-thing", "find-non-living-thing"} and focused:
        subject = norm(focused[-1])
    if family == "use-thermometer":
        non_tool = [value for value in acquired if "thermometer" not in value]
        if non_tool:
            subject = norm(non_tool[-1])
    return {
        "subject": norm(subject),
        "destination": norm(destination),
        "tool": "thermometer" if family == "use-thermometer" else "",
    }


def same_entity(value: str, expected: str) -> bool:
    left, right = role_name(value), role_name(expected)
    if left.startswith("egg ") and right != "egg":
        left = left.removeprefix("egg ")
    if left.endswith(" egg") and right != "egg":
        left = left.removesuffix(" egg")
    return bool(left and right) and (left == right or left in right or right in left)


def event_role(event: Event, roles: dict[str, str]) -> str:
    if "thermometer" in event.subject:
        return "tool"
    if same_entity(event.subject, roles.get("subject", "")):
        return "subject"
    return ""


def compile_call(
    *,
    call_id: str,
    actions: list[str],
    family: str,
    roles: dict[str, str],
    witness: str,
    schema_witness: str | None = None,
    goal_terminal: bool = False,
    validation_claims: Iterable[str] = (),
    validation_scope: str = "",
) -> dict:
    produced: set[str] = set()
    rely: set[str] = set()
    clobber: set[str] = set()
    bindings: dict[str, str] = {}
    for action in actions:
        event = parse_action(action)
        role = event_role(event, roles)
        if role:
            bindings[role] = roles[role]
        if event.operator == "go":
            produced.add(f"at:{role_name(event.subject)}")
        elif event.operator in {"open", "close"}:
            needed = f"at:{role_name(event.subject)}"
            if needed not in produced:
                rely.add(needed)
        elif event.operator == "acquire" and role:
            if event.target:
                needed = f"at:{role_name(event.target)}"
                if needed not in produced:
                    rely.add(needed)
            elif family.startswith("find-"):
                needed = f"focused:{role}"
                if needed not in produced:
                    rely.add(needed)
            produced.add(f"holds:{role}")
        elif event.operator == "focus" and role:
            if "inventory" in action.lower():
                needed = f"holds:{role}"
                if needed not in produced:
                    rely.add(needed)
            produced.add(f"focused:{role}")
        elif event.operator in {"clean", "cool", "heat"} and role == "subject":
            if "holds:subject" not in produced:
                rely.add("holds:subject")
            produced.add(f"transformed:{event.operator}:subject")
        elif event.operator == "measure" and role == "subject":
            for needed in ("holds:subject", "holds:tool", "focused:subject", "focused:tool"):
                if needed not in produced:
                    rely.add(needed)
            bindings["tool"] = roles.get("tool", "thermometer")
            produced.add("measured:subject")
        elif event.operator == "place" and role == "subject":
            needed = "focused:subject" if family == "find-non-living-thing" else "holds:subject"
            if needed not in produced:
                rely.add(needed)
            produced.add("delivered:subject")
            bindings["destination"] = norm(event.target)
            clobber.add("holds:subject")
        elif event.operator == "use" and family == "look_at_obj_in_light":
            if "holds:subject" not in produced:
                rely.add("holds:subject")
            produced.add("illuminated:subject")
            bindings["destination"] = norm(event.subject)
    if goal_terminal:
        produced.add("goal:complete")
    return {
        "call_id": call_id,
        "actions": actions,
        "contract": {
            "rely": sorted(rely),
            "guarantee": sorted(produced),
            "clobber": sorted(clobber),
            "bindings": bindings,
            "validate": sorted(validation_claims),
            "validation_scope": validation_scope,
            "effect_guard": {},
            "witnesses": sorted({witness, schema_witness} - {None}),
        },
    }


def segment_trace(record: dict) -> list[dict]:
    actions = record["executed_actions"]
    roles = infer_roles(record["family"], actions)
    witness = trace_hash(record)
    cuts = [index for index, action in enumerate(actions) if parse_action(action).operator in CRITICAL_OPERATORS]
    if not cuts or cuts[-1] != len(actions) - 1:
        cuts.append(len(actions) - 1)
    calls, start = [], 0
    for ordinal, end in enumerate(cuts):
        if end < start:
            continue
        segment = actions[start : end + 1]
        calls.append(compile_call(
            call_id=f"{witness[:12]}:{ordinal}",
            actions=segment,
            family=record["family"],
            roles=roles,
            witness=witness,
            goal_terminal=end == len(actions) - 1,
        ))
        start = end + 1
    return calls
