#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random


PROJECT = Path(__file__).resolve().parents[1]
ARMS = (
    "cgba", "no_repair", "pairwise_contract", "whole_chain_rollback",
    "llm_qwen3_4b", "llm_phi4_mini", "llm_mistral7b_v03",
)
CONFLICTS = ("rely_gap", "role_mismatch", "clobber", "stale_validation")


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seeded(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:16], 16)


def rate(values: list[dict], key: str) -> float:
    return sum(bool(row[key]) for row in values) / len(values) if values else 0.0


def summarize(values: list[dict]) -> dict:
    return {
        "n": len(values),
        "native_success_rate": rate(values, "native_success"),
        "constrained_success_rate": rate(values, "constrained_success"),
        "locality_rate": rate(values, "local"),
        "provenance_complete_rate": rate(values, "provenance_complete"),
        "adapter_command_support_rate": rate(values, "adapter_commands_supported"),
        "initial_state_match_rate": rate(values, "initial_state_match"),
        "technical_errors": sum(bool(row["technical_error"]) for row in values),
        "mean_proposed_adapter_actions": (
            sum(row["proposed_adapter_actions"] for row in values) / len(values)
            if values else 0.0
        ),
        "mean_executed_adapter_actions": (
            sum(row["executed_adapter_actions"] for row in values) / len(values)
            if values else 0.0
        ),
        "mean_executed_actions": (
            sum(row["executed_actions"] for row in values) / len(values)
            if values else 0.0
        ),
    }


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def clustered_inference(
    records: list[dict], bootstrap_replicates: int,
    randomization_replicates: int, seed: str,
) -> dict:
    by_task: dict[str, list[float]] = defaultdict(list)
    task_strata: dict[str, tuple[str, str]] = {}
    for row in records:
        by_task[row["task_id"]].append(row["difference"])
        task_strata[row["task_id"]] = row["environment"], row["family"]
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for task_id, stratum in task_strata.items():
        strata[stratum].append(task_id)
    rng = random.Random(seeded(seed + "|bootstrap"))
    bootstrap = []
    for _ in range(bootstrap_replicates):
        sampled = []
        for task_ids in strata.values():
            for _ in task_ids:
                sampled.extend(by_task[rng.choice(task_ids)])
        bootstrap.append(sum(sampled) / len(sampled))
    task_differences = [sum(values) / len(values) for values in by_task.values()]
    observed_task_macro = sum(task_differences) / len(task_differences)
    rng = random.Random(seeded(seed + "|randomization"))
    as_or_more_extreme = 0
    for _ in range(randomization_replicates):
        permuted = sum(
            value if rng.getrandbits(1) else -value for value in task_differences
        ) / len(task_differences)
        as_or_more_extreme += abs(permuted) >= abs(observed_task_macro) - 1e-15
    return {
        "incident_weighted_difference": sum(row["difference"] for row in records) / len(records),
        "task_macro_difference": observed_task_macro,
        "task_clusters": len(by_task),
        "strata": {"/".join(key): len(value) for key, value in sorted(strata.items())},
        "bootstrap_replicates": bootstrap_replicates,
        "bootstrap_95_percent_ci": [
            percentile(bootstrap, 0.025), percentile(bootstrap, 0.975)
        ],
        "paired_task_sign_randomization_replicates": randomization_replicates,
        "paired_task_sign_randomization_p_two_sided": (
            1 + as_or_more_extreme
        ) / (randomization_replicates + 1),
    }


def valid_label(row: dict) -> tuple[bool, str | None]:
    candidate = row["candidate"]
    common = (
        bool(row["source_oracle_success"])
        and bool(candidate["initial_state_match"])
        and not candidate["technical_error"]
    )
    if row["intended_class"] == "no_conflict":
        if common and candidate["success"] and row["matched_correction"] is None:
            return True, None
        return False, "control_source_or_candidate_not_valid"
    correction = row["matched_correction"]
    if (
        common and not candidate["success"] and correction is not None
        and correction["success"] and correction["initial_state_match"]
        and not correction["technical_error"]
    ):
        return True, None
    return False, "causal_failure_or_matched_correction_not_valid"


def provenance_complete(program: dict) -> bool:
    inserted = set(program.get("inserted_call_ids", []))
    calls = {call["call_id"]: call for call in program["calls"]}
    if not inserted <= set(calls):
        return False
    return all(
        not calls[call_id]["actions"]
        or bool(calls[call_id]["contract"].get("witnesses"))
        for call_id in inserted
    )


def evaluate_arm(
    arm: str, valid_ids: set[str], labels: dict[str, dict], public_ids: set[str]
) -> tuple[list[dict], dict]:
    program_path = PROJECT / "results/confirmation/programs" / arm / "programs.jsonl"
    outcome_path = PROJECT / "results/confirmation/native" / arm / "outcomes.jsonl"
    programs_list = rows(program_path)
    outcomes_list = rows(outcome_path)
    programs = {row["composition_id"]: row for row in programs_list}
    outcomes = {row["composition_id"]: row for row in outcomes_list}
    if len(programs) != len(programs_list) or len(outcomes) != len(outcomes_list):
        raise RuntimeError(f"Duplicate confirmation records for {arm}")
    if set(programs) != public_ids or set(outcomes) != public_ids:
        raise RuntimeError(f"Incomplete confirmation roster for {arm}")
    evaluated = []
    for composition_id in sorted(valid_ids):
        label = labels[composition_id]
        program = programs[composition_id]
        native = outcomes[composition_id]["outcome"]
        inserted = program.get("inserted_call_ids", [])
        wrapped = program.get("wrapped_original_call_ids", [])
        local = (
            bool(program.get("original_call_ids_unchanged", False))
            and len(inserted) <= 1 and len(wrapped) <= 1
        )
        provenance = provenance_complete(program)
        adapter_turns = [turn for turn in native["turns"] if turn.get("adapter_action", False)]
        supported = all(turn.get("adapter_command_supported", False) for turn in adapter_turns)
        native_success = bool(native["success"])
        inserted_set = set(inserted)
        proposed_adapter_actions = sum(
            len(call["actions"]) for call in program["calls"]
            if call["call_id"] in inserted_set
        )
        evaluated.append({
            "arm": arm,
            "composition_id": composition_id,
            "task_id": label["task_id"],
            "environment": label["environment"],
            "family": label["family"],
            "conflict_class": label["conflict_class"],
            "native_success": native_success,
            "constrained_success": native_success and local and provenance and supported,
            "local": local,
            "provenance_complete": provenance,
            "adapter_commands_supported": supported,
            "initial_state_match": bool(native["initial_state_match"]),
            "technical_error": native["technical_error"],
            "proposed_adapter_actions": proposed_adapter_actions,
            "executed_adapter_actions": len(adapter_turns),
            "executed_actions": len(native["turns"]),
            "wrapper_events": len(native.get("wrapper_events", [])),
        })
    causal = [row for row in evaluated if row["conflict_class"] != "no_conflict"]
    controls = [row for row in evaluated if row["conflict_class"] == "no_conflict"]
    by_class = defaultdict(list)
    by_environment = defaultdict(list)
    for row in evaluated:
        by_class[row["conflict_class"]].append(row)
        by_environment[row["environment"]].append(row)
    summary = {
        "arm": arm,
        "all_valid_incidents": summarize(evaluated),
        "causal_conflicts": summarize(causal),
        "healthy_controls": summarize(controls),
        "by_class": {key: summarize(value) for key, value in sorted(by_class.items())},
        "by_environment": {
            key: summarize(value) for key, value in sorted(by_environment.items())
        },
        "input_sha256": {
            "programs": digest(program_path), "native_outcomes": digest(outcome_path)
        },
    }
    return evaluated, summary


def main() -> None:
    config_path = PROJECT / "configs/confirmation.json"
    lock_path = PROJECT / "research/CONFIRMATION_METHOD_LOCK.json"
    roster_path = PROJECT / "data/confirmation/roster.json"
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    causal_path = PROJECT / "data/confirmation/causal_native/outcomes.jsonl"
    config = json.loads(config_path.read_text())
    lock = json.loads(lock_path.read_text())
    roster = json.loads(roster_path.read_text())
    public = rows(public_path)
    public_ids = {row["composition_id"] for row in public}
    causal = rows(causal_path)
    if len(causal) != len(public) or {row["spec_id"] for row in causal} != public_ids:
        raise RuntimeError("Causal labels and public incidents are incomplete or misaligned")
    label_rows = []
    for row in causal:
        valid, reason = valid_label(row)
        label_rows.append({
            "composition_id": row["spec_id"], "task_id": row["task_id"],
            "environment": row["environment"], "family": row["family"],
            "conflict_class": row["intended_class"], "valid": valid,
            "invalid_reason": reason,
            "candidate_success": bool(row["candidate"]["success"]),
            "matched_correction_success": (
                None if row["matched_correction"] is None
                else bool(row["matched_correction"]["success"])
            ),
        })
    labels = {row["composition_id"]: row for row in label_rows}
    valid_ids = {row["composition_id"] for row in label_rows if row["valid"]}
    arm_rows: dict[str, list[dict]] = {}
    arm_summaries = {}
    for arm in ARMS:
        arm_rows[arm], arm_summaries[arm] = evaluate_arm(
            arm, valid_ids, labels, public_ids
        )
    primary = lock["primary_method"]
    comparator = lock["primary_comparator"]
    method_map = {row["composition_id"]: row for row in arm_rows[primary]}
    comparator_map = {row["composition_id"]: row for row in arm_rows[comparator]}
    no_repair_map = {row["composition_id"]: row for row in arm_rows["no_repair"]}
    differences = [
        {
            **{key: method_map[composition_id][key] for key in (
                "composition_id", "task_id", "environment", "family", "conflict_class"
            )},
            "difference": (
                int(method_map[composition_id]["constrained_success"])
                - int(comparator_map[composition_id]["constrained_success"])
            ),
        }
        for composition_id in sorted(valid_ids)
        if labels[composition_id]["conflict_class"] != "no_conflict"
    ]
    inference = clustered_inference(
        differences, config["bootstrap_replicates"],
        config["randomization_replicates"], config["analysis_seed"],
    )
    valid_causal_ids = {
        composition_id for composition_id in valid_ids
        if labels[composition_id]["conflict_class"] != "no_conflict"
    }
    valid_control_ids = valid_ids - valid_causal_ids
    class_counts = Counter(labels[value]["conflict_class"] for value in valid_causal_ids)
    source_tasks = {labels[value]["task_id"] for value in valid_control_ids}

    def repair_gain(ids: set[str]) -> float:
        return sum(
            int(method_map[value]["constrained_success"])
            - int(no_repair_map[value]["constrained_success"])
            for value in ids
        ) / len(ids) if ids else 0.0

    class_repair_gains = {
        conflict: repair_gain({
            value for value in valid_causal_ids
            if labels[value]["conflict_class"] == conflict
        })
        for conflict in CONFLICTS
    }
    environments = sorted({labels[value]["environment"] for value in valid_causal_ids})
    environment_repair_gains = {
        environment: repair_gain({
            value for value in valid_causal_ids
            if labels[value]["environment"] == environment
        })
        for environment in environments
    }
    method = arm_summaries[primary]
    no_repair = arm_summaries["no_repair"]
    gates = config["gates"]
    control_loss = (
        no_repair["healthy_controls"]["native_success_rate"]
        - method["healthy_controls"]["native_success_rate"]
    )
    gain = inference["incident_weighted_difference"]
    checks = {
        "minimum_tasks": len(source_tasks) >= gates["minimum_tasks"],
        "minimum_causal_conflicts": len(valid_causal_ids) >= gates["minimum_causal_conflicts"],
        "minimum_controls": len(valid_control_ids) >= gates["minimum_controls"],
        "minimum_per_conflict_class": all(
            class_counts[conflict] >= gates["minimum_per_conflict_class"]
            for conflict in CONFLICTS
        ),
        "minimum_constrained_success": (
            method["causal_conflicts"]["constrained_success_rate"]
            >= gates["minimum_constrained_success"]
        ),
        "minimum_gain_over_frozen_comparator": gain >= gates["minimum_gain_points"] / 100,
        "bootstrap_interval_above_zero": inference["bootstrap_95_percent_ci"][0] > 0,
        "paired_randomization_p_at_most_alpha": (
            inference["paired_task_sign_randomization_p_two_sided"]
            <= gates["maximum_randomization_p"]
        ),
        "positive_repair_gain_every_conflict_class": all(
            value > 0 for value in class_repair_gains.values()
        ),
        "positive_repair_gain_both_environments": all(
            value > 0 for value in environment_repair_gains.values()
        ) and len(environment_repair_gains) == 2,
        "control_loss_at_most_two_points": control_loss <= gates["maximum_control_loss_points"] / 100,
        "minimum_95_percent_adapter_command_support": (
            method["causal_conflicts"]["adapter_command_support_rate"] >= 0.95
        ),
        "all_primary_repairs_local": method["causal_conflicts"]["locality_rate"] == 1,
        "all_primary_provenance_complete": (
            method["causal_conflicts"]["provenance_complete_rate"] == 1
        ),
        "all_primary_initial_states_match": (
            method["all_valid_incidents"]["initial_state_match_rate"] == 1
        ),
        "no_primary_technical_errors": method["all_valid_incidents"]["technical_errors"] == 0,
        "zero_overlap_roster": roster["overlap_with_prior_tasks"] == 0,
    }
    output = PROJECT / "results/confirmation/final"
    output.mkdir(parents=True, exist_ok=True)
    (output / "labels.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in label_rows)
    )
    all_evaluated = [row for arm in ARMS for row in arm_rows[arm]]
    (output / "evaluated.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in all_evaluated)
    )
    summary = {
        "status": "confirmation_gate_passed" if all(checks.values()) else "confirmation_gate_failed",
        "primary_method": primary,
        "frozen_primary_comparator": comparator,
        "validity": {
            "planned_incidents": len(label_rows),
            "valid_incidents": len(valid_ids),
            "invalid_incidents_excluded": len(label_rows) - len(valid_ids),
            "source_tasks_with_valid_controls": len(source_tasks),
            "valid_causal_conflicts": len(valid_causal_ids),
            "valid_controls": len(valid_control_ids),
            "valid_causal_by_class": dict(sorted(class_counts.items())),
        },
        "primary_inference": inference,
        "primary_constrained_success": method["causal_conflicts"]["constrained_success_rate"],
        "comparator_constrained_success": arm_summaries[comparator]["causal_conflicts"]["constrained_success_rate"],
        "gain_over_frozen_comparator": gain,
        "class_repair_gains_vs_no_repair": class_repair_gains,
        "environment_repair_gains_vs_no_repair": environment_repair_gains,
        "healthy_control_loss": control_loss,
        "checks": checks,
        "arms": arm_summaries,
        "claim_boundary": (
            "Controlled interface regressions on retained-witness text-simulator Skill programs; "
            "not arbitrary production failures or evidence that local repair always beats replanning."
        ),
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "roster": digest(roster_path), "public_incidents": digest(public_path),
            "causal_native": digest(causal_path), "analysis_script": digest(Path(__file__)),
        },
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (output / "arm_summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "arm", "causal_n", "causal_native_success", "causal_constrained_success",
            "control_n", "control_native_success", "adapter_command_support",
            "mean_proposed_adapter_actions",
        ])
        for arm in ARMS:
            value = arm_summaries[arm]
            writer.writerow([
                arm, value["causal_conflicts"]["n"],
                value["causal_conflicts"]["native_success_rate"],
                value["causal_conflicts"]["constrained_success_rate"],
                value["healthy_controls"]["n"],
                value["healthy_controls"]["native_success_rate"],
                value["causal_conflicts"]["adapter_command_support_rate"],
                value["causal_conflicts"]["mean_proposed_adapter_actions"],
            ])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
