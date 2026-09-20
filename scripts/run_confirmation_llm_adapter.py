#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "scripts"))
from cgba.adapters import diagnose_chain
from cgba.programs import build_llm_program
from run_llm_adapter import SYSTEM, parse, prompt


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-label", required=True)
    args = parser.parse_args()
    model_config_path = PROJECT / "configs/models.json"
    confirmation_config_path = PROJECT / "configs/confirmation.json"
    confirmation_config = json.loads(confirmation_config_path.read_text())
    lock_path = PROJECT / confirmation_config["paths"]["method_lock"]
    lock = json.loads(lock_path.read_text())
    if lock["status"] != "method_and_comparators_frozen_before_confirmation_roster":
        raise RuntimeError("Confirmation method lock is invalid")
    if (PROJECT / "data/confirmation/causal_native/outcomes.jsonl").exists():
        raise RuntimeError("LLM programs must be frozen before confirmation outcomes")
    config = json.loads(model_config_path.read_text())
    model_config = next(row for row in config["models"] if row["label"] == args.model_label)
    public_path = PROJECT / "data/confirmation/public_incidents.jsonl"
    incidents = rows(public_path)
    if not incidents:
        raise RuntimeError("Confirmation public incidents do not exist")
    arm = f"llm_{args.model_label}"
    output_dir = PROJECT / "results/confirmation/programs" / arm
    output_dir.mkdir(parents=True, exist_ok=True)
    response_path = output_dir / "responses.jsonl"
    program_path = output_dir / "programs.jsonl"
    run_spec = {
        "status": "paper13_confirmation_local_llm_adapter_before_native_outcomes",
        "output_schema_revision": 2,
        "arm": arm,
        "model": model_config,
        "seed": config["seed"],
        "maximum_generation_tokens": config["maximum_generation_tokens"],
        "input_sha256": {
            "models": digest(model_config_path),
            "confirmation_config": digest(confirmation_config_path),
            "method_lock": digest(lock_path),
            "public_incidents": digest(public_path),
            "development_prompt_runner": digest(PROJECT / "scripts/run_llm_adapter.py"),
            "program_builder": digest(PROJECT / "src/cgba/programs.py"),
            "system": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        },
        "hidden_labels_accessed": False,
        "matched_correction_programs_accessed": False,
        "native_outcomes_accessed": False,
    }
    run_spec_path = output_dir / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("Confirmation LLM adapter inputs changed")
    if not run_spec_path.exists():
        if response_path.exists() or program_path.exists():
            raise RuntimeError("Unowned confirmation LLM outputs")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(response_path)
    completed = {row["composition_id"] for row in saved}
    if len(saved) != len(completed):
        raise RuntimeError("Duplicate confirmation LLM responses")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_config["id"], revision=model_config["revision"], local_files_only=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_config["id"], revision=model_config["revision"], local_files_only=True,
        dtype="auto", device_map="cuda:0",
    ).eval()
    started = time.perf_counter()
    for ordinal, incident in enumerate(incidents, start=1):
        if incident["composition_id"] in completed:
            continue
        diagnosis = diagnose_chain(incident["calls"])
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt(incident, diagnosis)},
        ]
        try:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except TypeError:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
        tick = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(
                **inputs, do_sample=False,
                max_new_tokens=config["maximum_generation_tokens"],
                pad_token_id=tokenizer.eos_token_id,
            )
        generated_ids = generated[0, inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        prediction, parse_valid = parse(response)
        program = build_llm_program(
            incident=incident, diagnosis=diagnosis, prediction=prediction,
            model_label=args.model_label,
        )
        append(response_path, {
            "composition_id": incident["composition_id"],
            "diagnosis": diagnosis,
            "prediction": prediction,
            "parse_valid": parse_valid,
            "program_status": program["status"],
            "response": response,
            "input_tokens": int(inputs["input_ids"].shape[1]),
            "output_tokens": int(generated_ids.shape[0]),
            "elapsed_seconds": time.perf_counter() - tick,
        })
        completed.add(incident["composition_id"])
        print(json.dumps({
            "progress": f"{ordinal}/{len(incidents)}",
            "operation": prediction["operation"],
            "valid": parse_valid,
            "program_status": program["status"],
        }), flush=True)
    final_responses = rows(response_path)
    response_map = {row["composition_id"]: row for row in final_responses}
    if set(response_map) != {row["composition_id"] for row in incidents}:
        raise RuntimeError("Confirmation LLM generation is incomplete")
    programs = [
        build_llm_program(
            incident=incident,
            diagnosis=response_map[incident["composition_id"]]["diagnosis"],
            prediction=response_map[incident["composition_id"]]["prediction"],
            model_label=args.model_label,
        )
        for incident in incidents
    ]
    program_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in programs)
    )
    completion = {
        "status": "confirmation_programs_frozen_before_candidate_or_adapter_outcomes",
        "arm": arm,
        "model": model_config,
        "records": len(programs),
        "valid_outputs": sum(row["parse_valid"] for row in final_responses),
        "synthesized_programs": sum(row["status"] == "synthesized" for row in programs),
        "peak_cuda_memory_gib": torch.cuda.max_memory_reserved() / 1024**3,
        "elapsed_seconds_this_process": time.perf_counter() - started,
        "hidden_labels_accessed": False,
        "native_outcomes_accessed": False,
        "responses_sha256": digest(response_path),
        "programs_sha256": digest(program_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
