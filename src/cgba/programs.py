from __future__ import annotations

from copy import deepcopy
import re


def destructive_call_index(calls: list[dict], start: int) -> int | None:
    return next(
        (
            index
            for index in range(max(0, start), len(calls))
            if calls[index]["contract"]["clobber"]
            and calls[index]["contract"].get("effect_guard", {}).get("applicable", True)
        ),
        None,
    )


def repair_slot(diagnosis: dict, calls: list[dict]) -> dict:
    conflict = diagnosis["conflict_class"]
    boundary = diagnosis["boundary_index"]
    if conflict == "no_conflict":
        return {"operation": "noop"}
    if boundary is None:
        return {"operation": "abstain"}
    if conflict == "rely_gap":
        return {"operation": "insert_witness_prefix", "index": boundary + 1}
    if conflict == "role_mismatch":
        return {"operation": "replace_consumer", "index": boundary + 1}
    if conflict in {"clobber", "stale_validation"}:
        index = destructive_call_index(calls, boundary)
        return {
            "operation": "preservation_guard" if index is not None else "abstain",
            "index": index,
        }
    return {"operation": "abstain"}


def pairwise_diagnose(calls: list[dict]) -> dict:
    for index in range(len(calls) - 1):
        left = calls[index]["contract"]
        right = calls[index + 1]["contract"]
        mismatches = sorted(
            role for role, value in right["bindings"].items()
            if role in left["bindings"] and left["bindings"][role] != value
        )
        if mismatches:
            return {
                "conflict_class": "role_mismatch", "boundary_index": index,
                "evidence": mismatches,
            }
        destroyed = sorted(set(left["clobber"]) & set(right["rely"]))
        if destroyed and left.get("effect_guard", {}).get("applicable", True):
            return {
                "conflict_class": "clobber", "boundary_index": index,
                "evidence": destroyed,
            }
        missing = sorted(set(right["rely"]) - set(left["guarantee"]))
        if missing:
            return {
                "conflict_class": "rely_gap", "boundary_index": index,
                "evidence": missing,
            }
    return {"conflict_class": "no_conflict", "boundary_index": None, "evidence": []}


def build_llm_program(
    *, incident: dict, diagnosis: dict, prediction: dict, model_label: str
) -> dict:
    original = deepcopy(incident["calls"])
    calls = deepcopy(original)
    slot = repair_slot(diagnosis, calls)
    expected = slot["operation"]
    operation = prediction.get("operation", "abstain")
    inserted: list[str] = []
    wrapped: list[str] = []
    valid = operation == expected
    error = None
    if expected == "noop" and valid:
        pass
    elif expected == "insert_witness_prefix" and valid:
        source_ids = prediction.get("source_call_ids")
        witnesses = {call["call_id"]: call for call in incident["witness_calls"]}
        if (
            not isinstance(source_ids, list)
            or not source_ids
            or len(source_ids) != len(set(source_ids))
            or any(source_id not in witnesses for source_id in source_ids)
        ):
            valid, error = False, "invalid_witness_prefix_ids"
        else:
            ordered_ids = [call["call_id"] for call in incident["witness_calls"]]
            selected_positions = [ordered_ids.index(source_id) for source_id in source_ids]
            consumer_id = calls[slot["index"]]["call_id"]
            consumer_position = ordered_ids.index(consumer_id) if consumer_id in ordered_ids else -1
            existing_ids = {call["call_id"] for call in calls[:slot["index"]]}
            if (
                selected_positions != sorted(selected_positions)
                or consumer_position < 0
                or any(position >= consumer_position for position in selected_positions)
                or any(source_id in existing_ids for source_id in source_ids)
            ):
                valid, error = False, "witness_prefix_is_not_local_and_ordered"
            else:
                selected = [witnesses[source_id] for source_id in source_ids]
                guarantees = sorted({
                    value for call in selected for value in call["contract"]["guarantee"]
                })
                bindings: dict[str, str] = {}
                for call in selected:
                    bindings.update(call["contract"]["bindings"])
                adapter_id = f"adapter:llm:{model_label}:prefix:{incident['composition_id']}"
                adapter = {
                    "call_id": adapter_id,
                    "actions": [action for call in selected for action in call["actions"]],
                    "contract": {
                        "rely": sorted({
                            value for call in selected for value in call["contract"]["rely"]
                        } - set(guarantees)),
                        "guarantee": guarantees, "clobber": [], "bindings": bindings,
                        "validate": sorted({
                            value for call in selected for value in call["contract"]["validate"]
                        }),
                        "validation_scope": "llm-selected-witness-prefix",
                        "effect_guard": {},
                        "witnesses": sorted({
                            value for call in selected for value in call["contract"]["witnesses"]
                        }),
                    },
                    "adapter_metadata": {
                        "kind": expected, "model": model_label,
                        "source_call_ids": source_ids,
                    },
                }
                calls.insert(slot["index"], adapter)
                inserted.append(adapter_id)
    elif expected == "replace_consumer" and valid:
        source_id = prediction.get("source_call_id")
        source = next(
            (call for call in incident["witness_calls"] if call["call_id"] == source_id),
            None,
        )
        if source is None:
            valid, error = False, "unknown_witness_call_id"
        else:
            adapter = deepcopy(source)
            adapter["call_id"] = f"adapter:llm:{model_label}:{source_id}"
            adapter["adapter_metadata"] = {
                "kind": operation,
                "model": model_label,
                "source_call_id": source_id,
                "witnesses": source["contract"]["witnesses"],
            }
            wrapped.append(calls[slot["index"]]["call_id"])
            calls[slot["index"]] = adapter
            inserted.append(adapter["call_id"])
    elif expected == "preservation_guard" and valid:
        suppressed_id = prediction.get("suppressed_call_id")
        suppressed = calls[slot["index"]]
        if suppressed_id != suppressed["call_id"]:
            valid, error = False, "guard_does_not_name_diagnosed_call"
        else:
            adapter_id = f"adapter:llm:{model_label}:guard:{incident['composition_id']}"
            adapter = {
                "call_id": adapter_id,
                "actions": [],
                "contract": {
                    "rely": [], "guarantee": [], "clobber": [],
                    "bindings": suppressed["contract"]["bindings"], "validate": [],
                    "validation_scope": "llm-selected-preservation-guard",
                    "effect_guard": {}, "witnesses": suppressed["contract"]["witnesses"],
                },
                "adapter_metadata": {
                    "kind": expected, "model": model_label,
                    "suppressed_call_id": suppressed_id,
                },
            }
            calls[slot["index"]] = adapter
            inserted.append(adapter_id)
            wrapped.append(suppressed_id)
    else:
        valid = False
        error = "operation_mismatch_or_abstention"
    if not valid:
        calls = deepcopy(original)
        inserted, wrapped = [], []
    remaining_ids = [call["call_id"] for call in calls if not call["call_id"].startswith("adapter:")]
    expected_ids = [call["call_id"] for call in original if call["call_id"] not in wrapped]
    return {
        "composition_id": incident["composition_id"],
        "task_id": incident["task_id"],
        "environment": incident["environment"],
        "family": incident["family"],
        "diagnosis": diagnosis,
        "status": "synthesized" if valid else "abstained",
        "parse_or_validation_error": error,
        "calls": calls,
        "actions": [action for call in calls for action in call["actions"]],
        "inserted_call_ids": inserted,
        "wrapped_original_call_ids": wrapped,
        "original_call_ids_unchanged": remaining_ids == expected_ids,
    }


def _replace_terms(value: str, replacements: dict[str, str]) -> str:
    result = value
    for old in sorted(replacements, key=len, reverse=True):
        result = re.sub(rf"(?<!\w){re.escape(old)}(?!\w)", replacements[old], result)
    return result


def build_pairwise_contract_program(incident: dict, diagnosis: dict) -> dict:
    """Local comparator with no witness retrieval and no global liveness analysis."""
    original = deepcopy(incident["calls"])
    calls = deepcopy(original)
    boundary = diagnosis["boundary_index"]
    inserted: list[str] = []
    wrapped: list[str] = []
    status = "abstained"
    if diagnosis["conflict_class"] == "no_conflict":
        status = "synthesized"
    elif boundary is not None and boundary + 1 < len(calls):
        left, right = calls[boundary], calls[boundary + 1]
        left_contract, right_contract = left["contract"], right["contract"]
        mismatches = {
            old: left_contract["bindings"][role]
            for role, old in right_contract["bindings"].items()
            if role in left_contract["bindings"] and left_contract["bindings"][role] != old
        }
        if mismatches:
            adapter = deepcopy(right)
            adapter_id = f"adapter:pairwise:role:{right['call_id']}"
            adapter["call_id"] = adapter_id
            adapter["actions"] = [_replace_terms(action, mismatches) for action in right["actions"]]
            adapter["adapter_metadata"] = {"kind": "pairwise_role_substitution"}
            calls[boundary + 1] = adapter
            inserted.append(adapter_id)
            wrapped.append(right["call_id"])
            status = "synthesized"
        else:
            overlap = set(left_contract["clobber"]) & set(right_contract["rely"])
            if overlap and left_contract.get("effect_guard", {}).get("applicable", True):
                adapter_id = f"adapter:pairwise:guard:{incident['composition_id']}"
                calls[boundary] = {
                    "call_id": adapter_id,
                    "actions": [],
                    "contract": {
                        "rely": [], "guarantee": [], "clobber": [],
                        "bindings": left_contract["bindings"], "validate": [],
                        "validation_scope": "", "effect_guard": {}, "witnesses": [],
                    },
                    "adapter_metadata": {"kind": "pairwise_adjacent_preservation_guard"},
                }
                inserted.append(adapter_id)
                wrapped.append(left["call_id"])
                status = "synthesized"
    remaining_ids = [call["call_id"] for call in calls if not call["call_id"].startswith("adapter:")]
    expected_ids = [call["call_id"] for call in original if call["call_id"] not in wrapped]
    return {
        "composition_id": incident["composition_id"],
        "task_id": incident["task_id"],
        "environment": incident["environment"],
        "family": incident["family"],
        "diagnosis": diagnosis,
        "status": status,
        "calls": calls,
        "actions": [action for call in calls for action in call["actions"]],
        "inserted_call_ids": inserted,
        "wrapped_original_call_ids": wrapped,
        "original_call_ids_unchanged": remaining_ids == expected_ids,
    }
