from __future__ import annotations


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
        return {"conflict_class": "rely_gap", "boundary_index": None, "minimal_call_ids": [call["call_id"] for call in calls], "evidence": ["composition has fewer than two calls"]}

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

        effect_guard = contract.get("effect_guard", {})
        if contract["clobber"] and effect_guard:
            if not effect_guard.get("applicable", True):
                continue
            if effect_guard.get("goal_satisfying", False):
                return {
                    "conflict_class": "no_conflict",
                    "boundary_index": None,
                    "minimal_call_ids": [],
                    "evidence": ["intervening effect already satisfies the public goal"],
                }

        live = _future_relies(calls, index + 1)
        destroyed = sorted(set(contract["clobber"]) & state & live)
        if destroyed:
            stale = [predicate for predicate in destroyed if predicate in validated_at]
            if stale:
                return {
                    "conflict_class": "stale_validation",
                    **_boundary(calls, index - 1),
                    "evidence": [
                        f"{predicate} validated by call {validated_at[predicate]} then clobbered by call {index}"
                        for predicate in stale
                    ],
                }
            return {
                "conflict_class": "clobber",
                **_boundary(calls, index),
                "evidence": destroyed,
            }

        state.difference_update(contract["clobber"])
        state.update(contract["guarantee"])
        bindings.update(contract["bindings"])
        for predicate in contract["validate"]:
            if predicate in state:
                validated_at[predicate] = index

    if "goal:complete" not in state:
        return {
            "conflict_class": "rely_gap",
            **_boundary(calls, len(calls) - 2),
            "evidence": ["global goal is not guaranteed"],
        }
    return {"conflict_class": "no_conflict", "boundary_index": None, "minimal_call_ids": [], "evidence": []}


def pairwise_precondition_effect(calls: list[dict]) -> dict:
    state: set[str] = set()
    for index, call in enumerate(calls):
        missing = sorted(set(call["contract"]["rely"]) - state)
        if missing:
            return {"conflict_class": "rely_gap", **_boundary(calls, index - 1), "evidence": missing}
        state.update(call["contract"]["guarantee"])
    if "goal:complete" not in state:
        return {"conflict_class": "rely_gap", **_boundary(calls, len(calls) - 2), "evidence": ["global goal is not guaranteed"]}
    return {"conflict_class": "no_conflict", "boundary_index": None, "minimal_call_ids": [], "evidence": []}


def signature_match(calls: list[dict]) -> dict:
    bindings: dict[str, str] = {}
    for index, call in enumerate(calls):
        for role, value in call["contract"]["bindings"].items():
            if role in bindings and bindings[role] != value:
                return {"conflict_class": "role_mismatch", **_boundary(calls, index - 1), "evidence": [role]}
            bindings[role] = value
    return {"conflict_class": "no_conflict", "boundary_index": None, "minimal_call_ids": [], "evidence": []}
