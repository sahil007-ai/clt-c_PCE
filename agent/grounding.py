"""Numeric-grounding guard for coordinator explanations."""

from __future__ import annotations

import re
from collections.abc import Iterable


NUMBER_PATTERN = re.compile(r"(?<![A-Za-z-])\d+(?:\.\d+)?")


def _normalise(value: str | int | float) -> float:
    return round(float(value), 2)


def ungrounded_numbers(text: str, facts: Iterable[str | int | float]) -> list[str]:
    """Return numeric tokens in text that are not present in tool facts."""

    known = {_normalise(fact) for fact in facts}
    return [token for token in NUMBER_PATTERN.findall(text) if _normalise(token) not in known]


def verify_numeric_grounding(text: str, facts: Iterable[str | int | float]) -> bool:
    return not ungrounded_numbers(text, facts)
