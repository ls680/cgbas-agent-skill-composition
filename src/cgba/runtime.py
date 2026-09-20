from __future__ import annotations

import re


SCIENCEWORLD_REJECTIONS = (
    "no known action matches that input",
    "it's not clear how to get there from here",
    "i don't understand",
    "you can't",
)


def navigation_target(action: str) -> str | None:
    match = re.fullmatch(r"(?:go|teleport) to (.+)", action.lower().strip())
    return match.group(1) if match else None


def opened_target(action: str) -> str | None:
    text = action.lower().strip()
    for pattern in (r"open door to (.+)", r"open (.+)"):
        if match := re.fullmatch(pattern, text):
            return match.group(1)
    return None


def proven_idempotent_skip(
    *,
    action: str,
    admissible_actions: list[str],
    guarded: bool,
    current_location: str | None,
    opened: set[str],
) -> str | None:
    if not guarded or action in admissible_actions:
        return None
    destination = navigation_target(action)
    if destination is not None and destination == current_location:
        return "already_at_navigation_destination"
    target = opened_target(action)
    if target is not None and target in opened:
        return "already_open"
    return None


def update_runtime_state(
    *, action: str, current_location: str | None, opened: set[str]
) -> tuple[str | None, set[str]]:
    destination = navigation_target(action)
    if destination is not None:
        current_location = destination
    target = opened_target(action)
    if target is not None:
        opened = {*opened, target}
    return current_location, opened


def initial_runtime_state(observation: str) -> tuple[str | None, set[str]]:
    location_match = re.search(r"this room is called the ([^.]+)", observation, re.I)
    location = location_match.group(1).strip().lower() if location_match else None
    opened = set()
    for match in re.finditer(r"a door to ([^(\n]+) \(that is open\)", observation, re.I):
        target = match.group(1).strip().lower()
        opened.add(re.sub(r"^the\s+", "", target))
    return location, opened


def native_action_accepted(
    *, environment: str, listed_admissible: bool, observation: str
) -> bool:
    if environment == "alfworld":
        return listed_admissible
    normalized = " ".join(observation.lower().split()).rstrip(".")
    return not any(normalized.startswith(value) for value in SCIENCEWORLD_REJECTIONS)
