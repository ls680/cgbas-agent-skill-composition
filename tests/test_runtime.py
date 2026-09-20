from cgba.runtime import (
    initial_runtime_state,
    native_action_accepted,
    proven_idempotent_skip,
    update_runtime_state,
)


def test_guard_skips_only_proven_duplicate_navigation():
    assert proven_idempotent_skip(
        action="go to shelf 1",
        admissible_actions=["take apple 1 from shelf 1"],
        guarded=True,
        current_location="shelf 1",
        opened=set(),
    ) == "already_at_navigation_destination"
    assert proven_idempotent_skip(
        action="go to shelf 1",
        admissible_actions=[],
        guarded=False,
        current_location="shelf 1",
        opened=set(),
    ) is None


def test_guard_skips_only_previously_opened_receptacle():
    assert proven_idempotent_skip(
        action="open cabinet 1",
        admissible_actions=[],
        guarded=True,
        current_location="cabinet 1",
        opened={"cabinet 1"},
    ) == "already_open"


def test_runtime_state_tracks_navigation_and_opening():
    location, opened = update_runtime_state(
        action="go to cabinet 1", current_location=None, opened=set()
    )
    location, opened = update_runtime_state(
        action="open cabinet 1", current_location=location, opened=opened
    )
    assert location == "cabinet 1"
    assert opened == {"cabinet 1"}


def test_scienceworld_acceptance_does_not_treat_incomplete_action_list_as_grammar():
    assert native_action_accepted(
        environment="scienceworld", listed_admissible=False,
        observation="You move the unknown substance B to the green box.",
    )
    assert not native_action_accepted(
        environment="scienceworld", listed_admissible=False,
        observation="No known action matches that input.",
    )
    assert not native_action_accepted(
        environment="alfworld", listed_admissible=False, observation="Nothing happens.",
    )


def test_initial_scienceworld_state_parses_location_and_open_doors():
    location, opened = initial_runtime_state(
        "This room is called the hallway.\nA door to the kitchen (that is open)"
    )
    assert location == "hallway"
    assert opened == {"kitchen"}
