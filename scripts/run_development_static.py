#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from cgba.adapters import synthesize_adapter


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    input_path = PROJECT / "data/development/public_incidents.jsonl"
    output_dir = PROJECT / "results/development/static"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "adapters.jsonl"
    results = []
    for row in rows(input_path):
        try:
            repair = synthesize_adapter(
                calls=row["calls"],
                objective=row["objective"],
                witness_calls=row["witness_calls"],
            )
            results.append({
                "composition_id": row["composition_id"],
                "task_id": row["task_id"],
                "environment": row["environment"],
                "family": row["family"],
                "status": "synthesized",
                **repair,
            })
        except Exception as error:
            results.append({
                "composition_id": row["composition_id"],
                "task_id": row["task_id"],
                "environment": row["environment"],
                "family": row["family"],
                "status": "abstained",
                "error": f"{type(error).__name__}: {error}",
            })
    with output_path.open("w") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
    completion = {
        "status": "completed",
        "incidents": len(results),
        "synthesized": sum(row["status"] == "synthesized" for row in results),
        "abstained": sum(row["status"] == "abstained" for row in results),
        "input_sha256": digest(input_path),
        "method_sha256": digest(PROJECT / "src/cgba/adapters.py"),
        "outputs_sha256": digest(output_path),
        "hidden_label_file_accessed": False,
        "matched_correction_program_accessed": False,
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
