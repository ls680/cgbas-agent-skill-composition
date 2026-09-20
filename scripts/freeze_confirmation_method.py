#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
MODELS = ("qwen3_4b", "phi4_mini", "mistral7b_v03")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(path: str) -> dict:
    return json.loads((PROJECT / path).read_text())


def main() -> None:
    analyses = {
        "cgba": summary("results/development_v2/analysis/summary.json"),
        "no_repair": summary("results/development/comparators/no_repair/analysis/summary.json"),
        "pairwise_contract": summary("results/development/comparators/pairwise_contract/analysis/summary.json"),
        "whole_chain_rollback": summary("results/development/comparators/whole_chain_rollback/analysis/summary.json"),
        **{
            f"llm_{model}": summary(
                f"results/development/llm_adapters_v2/{model}/analysis/summary.json"
            )
            for model in MODELS
        },
    }
    deployable_local = (
        "no_repair", "pairwise_contract", "llm_qwen3_4b",
        "llm_phi4_mini", "llm_mistral7b_v03",
    )
    strongest = max(
        deployable_local,
        key=lambda arm: analyses[arm]["causal_conflicts"]["constrained_success_rate"],
    )
    method = analyses["cgba"]
    comparator = analyses[strongest]
    gain = (
        method["causal_conflicts"]["constrained_success_rate"]
        - comparator["causal_conflicts"]["constrained_success_rate"]
    )
    class_repair_gains = {
        conflict: (
            method["by_class"][conflict]["constrained_success_rate"]
            - analyses["no_repair"]["by_class"][conflict]["constrained_success_rate"]
        )
        for conflict in ("rely_gap", "role_mismatch", "clobber", "stale_validation")
    }
    class_comparator_differences = {
        conflict: (
            method["by_class"][conflict]["constrained_success_rate"]
            - comparator["by_class"][conflict]["constrained_success_rate"]
        )
        for conflict in ("rely_gap", "role_mismatch", "clobber", "stale_validation")
    }
    environment_repair_gains = {
        environment: (
            method["by_environment"][environment]["constrained_success_rate"]
            - analyses["no_repair"]["by_environment"][environment]["constrained_success_rate"]
        )
        for environment in ("alfworld", "scienceworld")
    }
    control_loss = (
        analyses["no_repair"]["healthy_controls"]["native_success_rate"]
        - method["healthy_controls"]["native_success_rate"]
    )
    checks = {
        "minimum_180_causal_conflicts": method["causal_conflicts"]["n"] >= 180,
        "minimum_60_controls": method["healthy_controls"]["n"] >= 60,
        "minimum_0_75_constrained_success": method["causal_conflicts"]["constrained_success_rate"] >= 0.75,
        "minimum_15_point_gain": gain >= 0.15,
        "positive_repair_gain_every_conflict_class": all(value > 0 for value in class_repair_gains.values()),
        "positive_repair_gain_both_environments": all(value > 0 for value in environment_repair_gains.values()),
        "control_loss_at_most_2_points": control_loss <= 0.02,
        "minimum_0_95_adapter_command_support": method["causal_conflicts"]["adapter_command_support_rate"] >= 0.95,
        "whole_chain_rollback_excluded_from_local_comparators": (
            analyses["whole_chain_rollback"]["causal_conflicts"]["constrained_success_rate"] == 0
            and analyses["whole_chain_rollback"]["causal_conflicts"]["native_success_rate"] == 1
        ),
    }
    gate = {
        "status": "development_gate_passed" if all(checks.values()) else "development_gate_failed",
        "strongest_deployable_local_comparator": strongest,
        "causal_constrained_success": method["causal_conflicts"]["constrained_success_rate"],
        "comparator_causal_constrained_success": comparator["causal_conflicts"]["constrained_success_rate"],
        "gain": gain, "class_repair_gains": class_repair_gains,
        "class_differences_vs_strongest_comparator": class_comparator_differences,
        "environment_repair_gains": environment_repair_gains,
        "control_loss": control_loss,
        "checks": checks,
        "all_development_arms": {
            arm: {
                "causal_native_success": value["causal_conflicts"]["native_success_rate"],
                "causal_constrained_success": value["causal_conflicts"]["constrained_success_rate"],
                "control_native_success": value["healthy_controls"]["native_success_rate"],
            }
            for arm, value in analyses.items()
        },
    }
    gate_path = PROJECT / "results/development/gate_summary.json"
    gate_path.write_text(json.dumps(gate, indent=2) + "\n")
    if gate["status"] != "development_gate_passed":
        raise RuntimeError("Development gate failed; confirmation is not authorized")
    files = (
        "configs/models.json", "configs/confirmation.json", "research/PROTOCOL.md",
        "research/development_revisions/REVISION2.md", "src/cgba/adapters.py",
        "src/cgba/programs.py", "src/cgba/runtime.py",
        "scripts/analyze_development_native.py", "scripts/build_prior_exclusions.py",
        "scripts/freeze_confirmation_roster.py", "scripts/collect_confirmation_oracles.py",
        "scripts/generate_confirmation_incidents.py", "scripts/build_confirmation_programs.py",
        "scripts/run_llm_adapter.py", "scripts/run_programs_native.py",
        "scripts/run_confirmation_llm_adapter.py", "scripts/analyze_confirmation.py",
        "scripts/run_confirmation_causal_native.py",
        "scripts/run_confirmation_programs_native.py", "scripts/run_confirmation_remote.sh",
        "../06_rely_guarantee_diagnosis/scripts/build_development_specs.py",
        "../06_rely_guarantee_diagnosis/scripts/run_development_native.py",
        "../01_skilllineage/src/skilllineage/interactive_envs.py",
        "../01_skilllineage/revisions/04_state_matched_execution/state_check.py",
        "../01_skilllineage/research/validation/vendor/scienceworld-e8216d6.jar",
    )
    lock = {
        "status": "method_and_comparators_frozen_before_confirmation_roster",
        "development_revision": 2, "remaining_revision_budget": 1,
        "primary_method": "cgba", "primary_comparator": strongest,
        "primary_endpoint": "constrained_native_repair_success",
        "development_gate_sha256": digest(gate_path),
        "prior_exclusions_sha256": digest(PROJECT / "data/confirmation/prior_exclusions.json"),
        "model_revisions": json.loads((PROJECT / "configs/models.json").read_text())["models"],
        "file_sha256": {path: digest(PROJECT / path) for path in files},
        "confirmation_rule": (
            "No code, prompt, model revision, comparator, endpoint, gate, roster, or "
            "analysis change after this lock without invalidating confirmation."
        ),
    }
    lock_path = PROJECT / "research/CONFIRMATION_METHOD_LOCK.json"
    if lock_path.exists() and json.loads(lock_path.read_text()) != lock:
        raise RuntimeError("Confirmation method lock already exists with different content")
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    print(json.dumps(gate, indent=2))
    print(json.dumps(lock, indent=2))


if __name__ == "__main__":
    main()
