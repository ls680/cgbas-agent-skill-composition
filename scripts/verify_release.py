#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ARMS = (
    "cgba", "no_repair", "pairwise_contract", "whole_chain_rollback",
    "llm_qwen3_4b", "llm_phi4_mini", "llm_mistral7b_v03",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    lock_path = PROJECT / "research/CONFIRMATION_METHOD_LOCK.json"
    lock = json.loads(lock_path.read_text())
    for relative, expected in lock["file_sha256"].items():
        path = PROJECT / relative
        check(path.exists(), f"Locked dependency is missing: {relative}")
        check(digest(path) == expected, f"Locked dependency changed: {relative}")
    exclusions = json.loads((PROJECT / "data/confirmation/prior_exclusions.json").read_text())
    roster = json.loads((PROJECT / "data/confirmation/roster.json").read_text())
    roster_ids = [row["task_id"] for row in roster["tasks"]]
    check(len(roster_ids) == len(set(roster_ids)) == 74, "Confirmation roster is not 74 unique tasks")
    check(not (set(roster_ids) & set(exclusions["excluded_task_ids"])), "Prior-task overlap detected")
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    public = rows(public_path)
    public_ids = {row["composition_id"] for row in public}
    check(len(public) == len(public_ids), "Public incidents are duplicated")
    causal_path = PROJECT / "data/confirmation/causal_native/outcomes.jsonl"
    causal = rows(causal_path)
    check({row["spec_id"] for row in causal} == public_ids, "Causal outcomes are incomplete")
    causal_spec = json.loads(
        (PROJECT / "data/confirmation/causal_native/run_spec.json").read_text()
    )
    program_paths = sorted((PROJECT / "results/confirmation/programs").glob("*/programs.jsonl"))
    check(len(program_paths) == len(ARMS), "Expected seven frozen program files")
    for index, path in enumerate(program_paths, start=1):
        check(
            causal_spec["input_sha256"][f"frozen_program_{index}"] == digest(path),
            f"Causal run did not freeze {path}",
        )
    for arm in ARMS:
        programs = rows(PROJECT / "results/confirmation/programs" / arm / "programs.jsonl")
        outcomes = rows(PROJECT / "results/confirmation/native" / arm / "outcomes.jsonl")
        check({row["composition_id"] for row in programs} == public_ids, f"Incomplete programs: {arm}")
        check({row["composition_id"] for row in outcomes} == public_ids, f"Incomplete outcomes: {arm}")
    for arm in ("llm_qwen3_4b", "llm_phi4_mini", "llm_mistral7b_v03"):
        spec = json.loads(
            (PROJECT / "results/confirmation/programs" / arm / "run_spec.json").read_text()
        )
        check(not spec["native_outcomes_accessed"], f"LLM program accessed outcomes: {arm}")
        check(not spec["hidden_labels_accessed"], f"LLM program accessed hidden labels: {arm}")
    summary_path = PROJECT / "results/confirmation/final/summary.json"
    summary = json.loads(summary_path.read_text())
    check(summary["status"] == "confirmation_gate_passed", "Confirmation gate did not pass")
    check(all(summary["checks"].values()), "At least one frozen confirmation check failed")
    for language in ("en", "zh"):
        check((PROJECT / "paper" / language / "main.pdf").exists(), f"Missing {language} PDF")
    result = {
        "status": "release_verified",
        "roster_tasks": len(roster_ids),
        "public_incidents": len(public_ids),
        "program_arms": len(program_paths),
        "confirmation_status": summary["status"],
        "method_lock_sha256": digest(lock_path),
        "confirmation_summary_sha256": digest(summary_path),
        "english_pdf_sha256": digest(PROJECT / "paper/en/main.pdf"),
        "chinese_pdf_sha256": digest(PROJECT / "paper/zh/main.pdf"),
    }
    destination = PROJECT / "artifacts/release_verification.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
