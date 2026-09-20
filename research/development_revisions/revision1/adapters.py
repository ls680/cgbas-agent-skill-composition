from __future__ import annotations

from copy import deepcopy
import re


def _boundary(calls: list[dict], index: int) -> dict:
    left = max(0, min(index, len(calls) - 2))
    return {
        "boundary_index": left,
        "minimal_call_ids": [calls[left]["call_id"], calls[left + 1]["call_id"]],
    }


def _future_relies(calls: list[dict], start: int) -> set[str]:
    needed: set[str] = set()
    for call in reversed(calls[start:]):
        contract = call["contract"]
        needed.difference_update(contract["guarantee"])
        needed.update(contract["rely"])
    needed.add("goal:complete")
    return needed


def diagnose_chain(calls: list[dict]) -> dict:
    if len(calls) < 2:
        return {"conflict_class": "rely_gap", "boundary_index": None, "evidence": []}
    state: set[str] = set()
    bindings: dict[str, str] = {}
    validated_at: dict[str, int] = {}
    for index, call in enumerate(calls):
        contract = call["contract"]
        for role, value in contract["bindings"].items():
            if role in bindings and bindings[role] != value:
                return {
                    "conflict_class": "role_mismatch",
                    **_boundary(calls, index - 1),
                    "evidence": [f"{role}:{bindings[role]}!={value}"],
                }
        missing = sorted(set(contract["rely"]) - state)
        if missing:
            return {
                "conflict_class": "rely_gap",
                **_boundary(calls, index - 1),
                "evidence": missing,
            }
        guard = contract.get("effect_guard", {})
        if contract["clobber"] and guard and not guard.get("applicable", True):
            continue
        if contract["clobber"] and guard.get("goal_satisfying", False):
            return {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []}
        live = _future_relies(calls, index + 1)
        destroyed = sorted(set(contract["clobber"]) & state & live)
        if destroyed:
            stale = [value for value in destroyed if value in validated_at]
            return {
                "conflict_class": "stale_validation" if stale else "clobber",
                **_boundary(calls, index - 1 if stale else index),
                "evidence": stale or destroyed,
            }
        state.difference_update(contract["clobber"])
        state.update(contract["guarantee"])
        bindings.update(contract["bindings"])
        for value in contract["validate"]:
            if value in state:
                validated_at[value] = index
    if "goal:complete" not in state:
        return {"conflict_class": "rely_gap", **_boundary(calls, len(calls) - 2), "evidence": ["goal:complete"]}
    return {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []}


def _state_before(calls: list[dict], stop: int) -> tuple[set[str], dict[str, str]]:
    state: set[str] = set()
    bindings: dict[str, str] = {}
    for call in calls[:stop]:
        contract = call["contract"]
        state.difference_update(contract["clobber"])
        state.update(contract["guarantee"])
        bindings.update(contract["bindings"])
    return state, bindings


def _objective_destination(objective: str) -> str | None:
    text = " ".join(objective.lower().split())
    patterns = (
        r"(?:on|in) (.+?)[.]?$",
        r"to the (.+?) in the [a-z ]+[.]?$",
    )
    for pattern in patterns:
        if match := re.search(pattern, text):
            return match.group(1).strip()
    return None


def _specialize_consumer(
    call: dict, live: dict[str, str], objective: str, witness_calls: list[dict]
) -> dict:
    witnessed = [
        candidate for candidate in witness_calls
        if "goal:complete" in candidate["contract"]["guarantee"]
        and all(
            role not in live or live[role] == value
            for role, value in candidate["contract"]["bindings"].items()
            if role != "destination"
        )
    ]
    if witnessed:
        source = min(witnessed, key=lambda value: (len(value["actions"]), value["call_id"]))
        result = deepcopy(source)
        result["adapter_metadata"] = {
            "kind": "witnessed_role_wrapper",
            "source_call_id": source["call_id"],
            "replaced_call_id": call["call_id"],
            "witnesses": source["contract"]["witnesses"],
        }
        result["call_id"] = f"adapter:role:{call['call_id']}"
        return result
    result = deepcopy(call)
    contract = result["contract"]
    replacements: dict[str, str] = {}
    for role, current in live.items():
        old = contract["bindings"].get(role)
        if old and old != current:
            replacements[old] = current
            contract["bindings"][role] = current
    destination = _objective_destination(objective)
    old_destination = contract["bindings"].get("destination")
    if destination and old_destination and old_destination != destination:
        replacements[old_destination] = destination
        contract["bindings"]["destination"] = destination
    result["actions"] = [
        _replace_terms(action, replacements) for action in result["actions"]
    ]
    result["adapter_metadata"] = {
        "kind": "role_mapping",
        "replacements": replacements,
        "source_call_id": call["call_id"],
    }
    result["call_id"] = f"adapter:role:{call['call_id']}"
    return result


def _replace_terms(value: str, replacements: dict[str, str]) -> str:
    result = value
    for old in sorted(replacements, key=len, reverse=True):
        result = re.sub(rf"(?<!\w){re.escape(old)}(?!\w)", replacements[old], result)
    return result


def _producer_adapter(
    missing: set[str], state: set[str], witness_calls: list[dict], boundary: int
) -> dict:
    candidates = []
    for call in witness_calls:
        contract = call["contract"]
        covers = missing & set(contract["guarantee"])
        unsatisfied = set(contract["rely"]) - state
        if covers and not unsatisfied:
            candidates.append((len(call["actions"]), call["call_id"], call, covers))
    if not candidates:
        raise RuntimeError(f"No witnessed producer establishes {sorted(missing)}")
    _, _, source, covers = min(candidates, key=lambda row: (row[0], row[1]))
    result = deepcopy(source)
    result["call_id"] = f"adapter:producer:{boundary}:{source['call_id']}"
    result["adapter_metadata"] = {
        "kind": "witnessed_producer",
        "restores": sorted(covers),
        "source_call_id": source["call_id"],
        "witnesses": source["contract"]["witnesses"],
    }
    return result


def _reacquire_adapter(call: dict, boundary: int, stale: bool) -> dict:
    contract = call["contract"]
    subject = contract["bindings"].get("subject")
    destination = contract.get("effect_guard", {}).get("effect_destination")
    if not subject or not destination:
        raise RuntimeError("Clobber recovery requires witnessed subject and destination")
    sample = " ".join(call["actions"]).lower()
    if "move " in sample and " in inventory to " not in sample:
        actions = [f"take {subject} from {destination}"]
    else:
        actions = [f"focus on {subject}", f"pick up {subject}"]
    kind = "restore_and_revalidate" if stale else "compensating_reacquisition"
    return {
        "call_id": f"adapter:{kind}:{boundary}:{call['call_id']}",
        "actions": actions,
        "contract": {
            "rely": [],
            "guarantee": ["holds:subject"],
            "clobber": [],
            "bindings": {"subject": subject},
            "validate": ["holds:subject"] if stale else [],
            "validation_scope": "post-compensation" if stale else "",
            "effect_guard": {},
            "witnesses": contract["witnesses"],
        },
        "adapter_metadata": {
            "kind": kind,
            "restores": ["holds:subject"],
            "source_call_id": call["call_id"],
            "witnesses": contract["witnesses"],
        },
    }


def synthesize_adapter(
    *, calls: list[dict], objective: str, witness_calls: list[dict]
) -> dict:
    original = deepcopy(calls)
    diagnosis = diagnose_chain(original)
    conflict = diagnosis["conflict_class"]
    boundary = diagnosis["boundary_index"]
    repaired = deepcopy(original)
    inserted: list[str] = []
    wrapped: list[str] = []
    if conflict == "no_conflict":
        pass
    elif conflict == "rely_gap":
        consumer = boundary + 1
        state, _ = _state_before(repaired, consumer)
        missing = set(repaired[consumer]["contract"]["rely"]) - state
        adapter = _producer_adapter(missing, state, witness_calls, boundary)
        repaired.insert(consumer, adapter)
        inserted.append(adapter["call_id"])
    elif conflict == "role_mismatch":
        consumer = boundary + 1
        _, live = _state_before(repaired, consumer)
        adapter = _specialize_consumer(
            repaired[consumer], live, objective, witness_calls
        )
        wrapped.append(repaired[consumer]["call_id"])
        repaired[consumer] = adapter
        inserted.append(adapter["call_id"])
    elif conflict in {"clobber", "stale_validation"}:
        start = boundary if conflict == "stale_validation" else boundary
        clobber_index = next(
            (
                index for index in range(start, len(repaired))
                if repaired[index]["contract"]["clobber"]
                and repaired[index]["contract"].get("effect_guard", {}).get("applicable", True)
            ),
            None,
        )
        if clobber_index is None:
            raise RuntimeError("Diagnosed clobber has no applicable destructive call")
        adapter = _reacquire_adapter(
            repaired[clobber_index], boundary, conflict == "stale_validation"
        )
        repaired.insert(clobber_index + 1, adapter)
        inserted.append(adapter["call_id"])
    else:
        raise RuntimeError(f"Unsupported diagnosis: {conflict}")
    return {
        "diagnosis": diagnosis,
        "calls": repaired,
        "actions": [action for call in repaired for action in call["actions"]],
        "inserted_call_ids": inserted,
        "wrapped_original_call_ids": wrapped,
        "original_call_ids_unchanged": all(
            before["call_id"] == after["call_id"]
            for before, after in zip(
                [call for call in original if call["call_id"] not in wrapped],
                [call for call in repaired if not call["call_id"].startswith("adapter:")],
            )
        ),
    }
