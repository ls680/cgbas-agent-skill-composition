#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from cgba.adapters import diagnose_chain
from cgba.programs import build_llm_program, repair_slot


SYSTEM = """You repair one diagnosed boundary in an ordered LLM-agent Skill composition.
Preserve every original Skill artifact and change only the diagnosed handoff with at most one
adapter. Use noop for no_conflict. For rely_gap, use insert_witness_prefix and select every needed
not-yet-executed source call_id in original witness order. For role_mismatch, use replace_consumer
and select one exact witness call_id. For clobber or stale_validation, use preservation_guard and
name the exact destructive candidate call_id that must not execute. Do not emit explanations,
plans, generated commands, or a whole replacement chain. Return one JSON object only. If no valid
local repair is supported, return {"operation":"abstain"}."""


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


def prompt(row: dict, diagnosis: dict) -> str:
    slot = repair_slot(diagnosis, row["calls"])
    schemas = {
        "noop": '{"operation":"noop"}',
        "insert_witness_prefix": '{"operation":"insert_witness_prefix","source_call_ids":["EXACT_ID_1","EXACT_ID_2"]}',
        "replace_consumer": '{"operation":"replace_consumer","source_call_id":"EXACT_ID"}',
        "preservation_guard": '{"operation":"preservation_guard","suppressed_call_id":"EXACT_CANDIDATE_ID"}',
        "abstain": '{"operation":"abstain"}',
    }
    calls = [{
        "index": index,
        "call_id": call["call_id"],
        "actions": call["actions"],
        "contract": call["contract"],
    } for index, call in enumerate(row["calls"])]
    witnesses = [{
        "call_id": call["call_id"],
        "actions": call["actions"],
        "contract": call["contract"],
    } for call in row["witness_calls"]]
    return (
        f"Environment: {row['environment']}\nFamily: {row['family']}\n"
        f"Objective: {row['objective']}\nInitial observation: {row['initial_observation']}\n"
        f"Diagnosis: {json.dumps(diagnosis, sort_keys=True)}\n"
        f"Allowed schemas: {json.dumps(schemas, sort_keys=True)}\n"
        f"Candidate calls: {json.dumps(calls, sort_keys=True)}\n"
        f"Witness catalog: {json.dumps(witnesses, sort_keys=True)}"
    )


def parse(text: str) -> tuple[dict, bool]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.I).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.S)
    if not match:
        return {"operation": "abstain"}, False
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"operation": "abstain"}, False
    valid = isinstance(value, dict) and value.get("operation") in {
        "noop", "insert_witness_prefix", "replace_consumer", "preservation_guard", "abstain"
    }
    return (value if valid else {"operation": "abstain"}), valid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-label", required=True)
    parser.add_argument("--output-variant", default="llm_adapters_v2")
    args = parser.parse_args()
    config_path = PROJECT / "configs/models.json"
    config = json.loads(config_path.read_text())
    model_config = next(row for row in config["models"] if row["label"] == args.model_label)
    public_path = PROJECT / "data/development/public_incidents.jsonl"
    incidents = rows(public_path)
    output_dir = PROJECT / "results/development" / args.output_variant / args.model_label
    output_dir.mkdir(parents=True, exist_ok=True)
    response_path = output_dir / "responses.jsonl"
    program_path = output_dir / "programs.jsonl"
    run_spec = {
        "status": "paper13_development_local_llm_adapter",
        "output_schema_revision": 2,
        "model": model_config,
        "seed": config["seed"],
        "maximum_generation_tokens": config["maximum_generation_tokens"],
        "public_incidents_sha256": digest(public_path),
        "system_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "hidden_labels_accessed": False,
        "matched_correction_programs_accessed": False,
        "native_outcomes_accessed": False,
    }
    run_spec_path = output_dir / "run_spec.json"
    if run_spec_path.exists() and json.loads(run_spec_path.read_text()) != run_spec:
        raise RuntimeError("LLM adapter inputs changed")
    if not run_spec_path.exists():
        if response_path.exists() or program_path.exists():
            raise RuntimeError("Unowned LLM adapter outputs")
        run_spec_path.write_text(json.dumps(run_spec, indent=2) + "\n")
    saved = rows(response_path)
    completed = {row["composition_id"] for row in saved}
    if len(saved) != len(completed):
        raise RuntimeError("Duplicate LLM responses")

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
    for ordinal, row in enumerate(incidents, start=1):
        if row["composition_id"] in completed:
            continue
        diagnosis = diagnose_chain(row["calls"])
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt(row, diagnosis)},
        ]
        try:
            rendered = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
        except TypeError:
            rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
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
            incident=row, diagnosis=diagnosis, prediction=prediction,
            model_label=args.model_label,
        )
        result = {
            "composition_id": row["composition_id"],
            "diagnosis": diagnosis,
            "prediction": prediction,
            "parse_valid": parse_valid,
            "program_status": program["status"],
            "response": response,
            "input_tokens": int(inputs["input_ids"].shape[1]),
            "output_tokens": int(generated_ids.shape[0]),
            "elapsed_seconds": time.perf_counter() - tick,
        }
        append(response_path, result)
        completed.add(row["composition_id"])
        print(json.dumps({
            "progress": f"{ordinal}/{len(incidents)}",
            "operation": prediction["operation"],
            "valid": parse_valid,
            "program_status": program["status"],
        }), flush=True)
    final_responses = rows(response_path)
    response_map = {row["composition_id"]: row for row in final_responses}
    programs = []
    for row in incidents:
        result = response_map[row["composition_id"]]
        programs.append(build_llm_program(
            incident=row,
            diagnosis=result["diagnosis"],
            prediction=result["prediction"],
            model_label=args.model_label,
        ))
    program_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in programs))
    completion = {
        "status": "completed",
        "model": model_config,
        "records": len(programs),
        "valid_outputs": sum(row["parse_valid"] for row in final_responses),
        "synthesized_programs": sum(row["status"] == "synthesized" for row in programs),
        "peak_cuda_memory_gib": torch.cuda.max_memory_reserved() / 1024**3,
        "elapsed_seconds_this_process": time.perf_counter() - started,
        "responses_sha256": digest(response_path),
        "programs_sha256": digest(program_path),
    }
    (output_dir / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
