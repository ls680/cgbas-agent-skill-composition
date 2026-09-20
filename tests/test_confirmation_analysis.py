from __future__ import annotations

import sys
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
from analyze_confirmation import percentile, provenance_complete, valid_label


def causal_row(candidate_success: bool = False, correction_success: bool = True) -> dict:
    return {
        "source_oracle_success": True,
        "intended_class": "rely_gap",
        "candidate": {
            "success": candidate_success, "initial_state_match": True,
            "technical_error": None,
        },
        "matched_correction": {
            "success": correction_success, "initial_state_match": True,
            "technical_error": None,
        },
    }


def test_causal_label_requires_failure_and_successful_matched_correction() -> None:
    assert valid_label(causal_row()) == (True, None)
    assert not valid_label(causal_row(candidate_success=True))[0]
    assert not valid_label(causal_row(correction_success=False))[0]


def test_empty_guard_has_no_command_provenance_obligation() -> None:
    program = {
        "inserted_call_ids": ["adapter:guard"],
        "calls": [{
            "call_id": "adapter:guard", "actions": [],
            "contract": {"witnesses": []},
        }],
    }
    assert provenance_complete(program)
    program["calls"][0]["actions"] = ["take object"]
    assert not provenance_complete(program)


def test_percentile_interpolates() -> None:
    assert percentile([0.0, 1.0], 0.25) == 0.25
