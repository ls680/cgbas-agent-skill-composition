from cgba.adapters import diagnose_chain, synthesize_adapter


def call(call_id, *, actions=(), rely=(), guarantee=(), clobber=(), bindings=None, guard=None, validate=()):
    return {
        "call_id": call_id,
        "actions": list(actions),
        "contract": {
            "rely": list(rely),
            "guarantee": list(guarantee),
            "clobber": list(clobber),
            "bindings": bindings or {},
            "validate": list(validate),
            "validation_scope": "",
            "effect_guard": guard or {},
            "witnesses": ["witness"],
        },
    }


def test_missing_rely_inserts_shortest_witnessed_producer():
    candidate = [call("neutral"), call("place", actions=["move apple 1 to desk 1"], rely=["holds:subject"], guarantee=["goal:complete"], bindings={"subject": "apple 1", "destination": "desk 1"})]
    witness = [call("acquire", actions=["take apple 1 from shelf 1"], guarantee=["holds:subject"], bindings={"subject": "apple 1"})]

    result = synthesize_adapter(calls=candidate, objective="put some apple on desk.", witness_calls=witness)

    assert result["diagnosis"]["conflict_class"] == "rely_gap"
    assert result["calls"][1]["adapter_metadata"]["kind"] == "witnessed_producer"
    assert result["actions"] == ["take apple 1 from shelf 1", "move apple 1 to desk 1"]


def test_role_wrapper_rebinds_subject_and_public_destination():
    candidate = [
        call("producer", guarantee=["holds:subject"], bindings={"subject": "apple 1"}),
        call("consumer", actions=["go to shelf 1", "move mug 2 to shelf 1"], rely=["holds:subject"], guarantee=["goal:complete"], bindings={"subject": "mug 2", "destination": "shelf 1"}),
    ]

    witness = [
        call("witness-consumer", actions=["go to desk 1", "move apple 1 to desk 1"], rely=["holds:subject"], guarantee=["goal:complete"], bindings={"subject": "apple 1", "destination": "desk 1"})
    ]
    result = synthesize_adapter(calls=candidate, objective="put some apple on desk.", witness_calls=witness)

    assert result["diagnosis"]["conflict_class"] == "role_mismatch"
    assert result["actions"] == ["go to desk 1", "move apple 1 to desk 1"]


def test_clobber_wraps_destructive_call_with_preservation_guard():
    candidate = [
        call("producer", guarantee=["holds:subject"], bindings={"subject": "apple 1"}),
        call("clobber", actions=["move apple 1 to shelf 1"], rely=["holds:subject"], clobber=["holds:subject"], bindings={"subject": "apple 1"}, guard={"applicable": True, "effect_destination": "shelf 1"}),
        call("consumer", actions=["move apple 1 to desk 1"], rely=["holds:subject"], guarantee=["goal:complete"]),
    ]

    result = synthesize_adapter(calls=candidate, objective="put some apple on desk.", witness_calls=[])

    assert result["diagnosis"]["conflict_class"] == "clobber"
    assert "move apple 1 to shelf 1" not in result["actions"]
    assert "move apple 1 to desk 1" in result["actions"]
    assert result["wrapped_original_call_ids"] == ["clobber"]
    assert result["inserted_call_ids"][0].startswith("adapter:live_state_preserving_guard:")


def test_healthy_chain_is_unchanged():
    candidate = [
        call("producer", actions=["take apple 1 from shelf 1"], guarantee=["holds:subject"]),
        call("consumer", actions=["move apple 1 to desk 1"], rely=["holds:subject"], guarantee=["goal:complete"]),
    ]

    assert diagnose_chain(candidate)["conflict_class"] == "no_conflict"
    result = synthesize_adapter(calls=candidate, objective="put some apple on desk.", witness_calls=[])
    assert result["actions"] == ["take apple 1 from shelf 1", "move apple 1 to desk 1"]
    assert result["inserted_call_ids"] == []
