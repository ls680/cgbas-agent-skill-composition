#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
PAPER6 = PROJECT.parent / "06_rely_guarantee_diagnosis"
sys.path.insert(0, str(PAPER6 / "scripts"))
import build_development_specs as generator


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config_path = PROJECT / "configs/confirmation.json"
    config = json.loads(config_path.read_text())
    paths = config["paths"]
    lock_path = PROJECT / paths["method_lock"]
    roster_path = PROJECT / paths["roster"]
    oracle_path = PROJECT / paths["oracles"] / "trajectories.jsonl"
    if json.loads(lock_path.read_text())["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Method lock is invalid")
    if json.loads(roster_path.read_text())["status"] != "content_blind_zero_overlap_roster_frozen_before_source_outcomes":
        raise RuntimeError("Roster is invalid")
    records = [row for row in rows(oracle_path) if row["success"] and not row["error"]]
    bases = {
        (row["environment"], row["task_id"]): generator.segment_trace(row)
        for row in records
    }
    roles = {
        (row["environment"], row["task_id"]): generator.infer_roles(
            row["family"], row["executed_actions"]
        )
        for row in records
    }
    donors: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        donors.setdefault((record["environment"], record["family"]), []).append(record)

    specs = []
    public = []
    for record in records:
        key = record["environment"], record["task_id"]
        base = bases[key]
        if len(base) < 2:
            continue
        task_specs = [generator.spec(record, "no_conflict", base, base, None)]
        witness = generator.trace_hash(record)
        neutral = generator.compile_call(
            call_id=f"{witness[:12]}:neutral",
            actions=["look" if record["environment"] == "alfworld" else "look around"],
            family=record["family"], roles=roles[key], witness=witness,
        )
        task_specs.append(generator.spec(record, "rely_gap", [neutral, base[-1]], base, 0))
        clobber = generator.make_clobber(record, base)
        if clobber is not None:
            inserted = len(base) - 1
            task_specs.append(generator.spec(
                record, "clobber", base[:-1] + [clobber, base[-1]], base, inserted
            ))
        current_subject = roles[key]["subject"]
        alternatives = [
            donor for donor in donors[(record["environment"], record["family"])]
            if donor["task_id"] != record["task_id"]
            and generator.infer_roles(donor["family"], donor["executed_actions"])["subject"] != current_subject
            and "subject" in bases[(donor["environment"], donor["task_id"])][-1]["contract"]["bindings"]
        ]
        if alternatives:
            donor = min(alternatives, key=lambda row: hashlib.sha256(
                f"{config['generation_seed']}|{record['task_id']}|{row['task_id']}".encode()
            ).hexdigest())
            donor_call = bases[(donor["environment"], donor["task_id"])][-1]
            candidate = base[:-1] + [donor_call]
            task_specs.append(generator.spec(
                record, "role_mismatch", candidate, base, len(candidate) - 2,
                {"donor_task_id": donor["task_id"]},
            ))
        if clobber is not None:
            validation = generator.compile_call(
                call_id=f"{witness[:12]}:local-validator", actions=[],
                family=record["family"], roles=roles[key], witness=witness,
                validation_claims=["holds:subject"],
                validation_scope="post-acquisition handoff",
            )
            validation["contract"]["rely"] = ["holds:subject"]
            prefix = base[:-1]
            task_specs.append(generator.spec(
                record, "stale_validation",
                prefix + [validation, clobber, base[-1]], base, len(prefix),
            ))
        specs.extend(task_specs)
        for spec in task_specs:
            public.append({
                "composition_id": spec["spec_id"],
                "task_id": spec["task_id"],
                "environment": spec["environment"],
                "family": spec["family"],
                "objective": spec["objective"],
                "initial_observation": record["observations"][0],
                "calls": spec["candidate_calls"],
                "witness_calls": base,
                "information_boundary": [
                    "public objective", "candidate calls", "MRGD-compatible contracts",
                    "provenance-linked successful witness calls",
                ],
            })
    artifact = {
        "status": "confirmation_incidents_frozen_before_candidate_or_matched_outcomes",
        "native_mutation_outcomes_read_by_generator": False,
        "successful_source_tasks": len(records), "spec_count": len(specs),
        "by_environment": dict(Counter(row["environment"] for row in specs)),
        "by_intended_class": dict(Counter(row["intended_class"] for row in specs)),
        "input_sha256": {
            "config": digest(config_path), "method_lock": digest(lock_path),
            "roster": digest(roster_path), "oracles": digest(oracle_path),
            "generator": digest(Path(__file__)),
            "paper6_segmentation_and_contract_compiler": digest(PAPER6 / "scripts/build_development_specs.py"),
        },
        "specs": specs,
    }
    spec_path = PROJECT / "data/confirmation/specs.json"
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    if spec_path.exists() or public_path.exists():
        raise RuntimeError("Confirmation incidents already exist")
    spec_path.write_text(json.dumps(artifact, indent=2) + "\n")
    public_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in public))
    completion = {
        "status": artifact["status"], "source_tasks": len(records),
        "specs": len(specs), "public_records": len(public),
        "by_environment": artifact["by_environment"],
        "by_intended_class": artifact["by_intended_class"],
        "specs_sha256": digest(spec_path), "public_incidents_sha256": digest(public_path),
    }
    (PROJECT / "data/confirmation/incidents_completion.json").write_text(
        json.dumps(completion, indent=2) + "\n"
    )
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
