from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Event:
    operator: str
    subject: str = ""
    target: str = ""


def norm(value: str) -> str:
    value = re.sub(r"\s+", " ", value.lower().strip().rstrip("."))
    value = re.sub(r"^(?:the|a|an|some) ", "", value)
    value = re.sub(r"\s+in inventory$", "", value)
    return value


def role_name(value: str) -> str:
    return re.sub(r"\s+\d+$", "", norm(value))


def parse_action(action: str) -> Event:
    text = re.sub(r"\s+", " ", action.lower().strip())
    patterns = (
        (r"go to (.+)", "go"),
        (r"teleport to (.+)", "go"),
        (r"open door to (.+)", "open_door"),
        (r"open (.+)", "open"),
        (r"close (.+)", "close"),
        (r"take (.+) from (.+)", "acquire"),
        (r"pick up (.+)", "acquire"),
        (r"move (.+?) (?:to|into) (.+)", "place"),
        (r"clean (.+) with (.+)", "clean"),
        (r"cool (.+) with (.+)", "cool"),
        (r"heat (.+) with (.+)", "heat"),
        (r"focus on (.+)", "focus"),
        (r"use thermometer(?: in inventory)? on (.+)", "measure"),
        (r"use (.+)", "use"),
    )
    for pattern, operator in patterns:
        matched = re.fullmatch(pattern, text)
        if matched:
            values = [norm(value) for value in matched.groups()]
            return Event(operator, values[0], values[1] if len(values) > 1 else "")
    return Event("other", norm(text), "")
