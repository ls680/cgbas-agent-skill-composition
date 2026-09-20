from cgba.programs import build_llm_program, repair_slot


def contract(**values):
    base = {
        "rely": [], "guarantee": [], "clobber": [], "bindings": {},
        "validate": [], "validation_scope": "", "effect_guard": {}, "witnesses": ["w"],
    }
    base.update(values)
    return base


def incident():
    witness = {"call_id": "w:0", "actions": ["take apple 1 from shelf 1"], "contract": contract(guarantee=["holds:subject"])}
    witness_consumer = {
        "call_id": "consumer", "actions": ["put apple 1 in box 1"],
        "contract": contract(rely=["holds:subject"], guarantee=["goal:complete"]),
    }
    return {
        "composition_id": "c", "task_id": "t", "environment": "alfworld", "family": "f",
        "calls": [
            {"call_id": "neutral", "actions": ["look"], "contract": contract()},
            {"call_id": "consumer", "actions": ["put apple 1 in box 1"], "contract": contract(rely=["holds:subject"])},
        ],
        "witness_calls": [witness, witness_consumer],
    }


def test_repair_slot_places_missing_rely_before_consumer():
    assert repair_slot({"conflict_class": "rely_gap", "boundary_index": 0}, incident()["calls"]) == {
        "operation": "insert_witness_prefix", "index": 1
    }


def test_llm_witness_selection_preserves_original_calls():
    program = build_llm_program(
        incident=incident(),
        diagnosis={"conflict_class": "rely_gap", "boundary_index": 0, "evidence": ["holds:subject"]},
        prediction={"operation": "insert_witness_prefix", "source_call_ids": ["w:0"]},
        model_label="test",
    )
    assert program["status"] == "synthesized"
    assert program["original_call_ids_unchanged"]
    assert [call["call_id"] for call in program["calls"]] == [
        "neutral", "adapter:llm:test:prefix:c", "consumer"
    ]


def test_invalid_llm_witness_abstains_without_editing_program():
    program = build_llm_program(
        incident=incident(),
        diagnosis={"conflict_class": "rely_gap", "boundary_index": 0, "evidence": ["holds:subject"]},
        prediction={"operation": "insert_witness_prefix", "source_call_ids": ["missing"]},
        model_label="test",
    )
    assert program["status"] == "abstained"
    assert program["actions"] == ["look", "put apple 1 in box 1"]


def test_llm_guard_names_and_suppresses_only_diagnosed_call():
    row = incident()
    row["calls"] = [
        {"call_id": "producer", "actions": ["take apple"], "contract": contract(guarantee=["holds:subject"])},
        {"call_id": "bad", "actions": ["drop apple"], "contract": contract(clobber=["holds:subject"], effect_guard={"applicable": True})},
        {"call_id": "consumer", "actions": ["put apple"], "contract": contract(rely=["holds:subject"], guarantee=["goal:complete"])},
    ]
    program = build_llm_program(
        incident=row,
        diagnosis={"conflict_class": "clobber", "boundary_index": 1, "evidence": ["holds:subject"]},
        prediction={"operation": "preservation_guard", "suppressed_call_id": "bad"},
        model_label="test",
    )
    assert program["status"] == "synthesized"
    assert "drop apple" not in program["actions"]
    assert program["wrapped_original_call_ids"] == ["bad"]
