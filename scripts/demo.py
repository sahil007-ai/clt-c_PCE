"""Short terminal demonstration for the normal and disrupted scheduling flows."""

from __future__ import annotations

from agent.graph import coordinate_plan
from engine.generate import load_planning_input
from engine.schemas import ObjectiveWeights


def show(title: str, event: dict | None = None) -> None:
    result = coordinate_plan(
        load_planning_input(), ObjectiveWeights(cost=60, availability=30, health=10), event=event
    )
    print(f"\n{title}")
    print(result.explanation)
    print(f"Verified: {result.selected.check.valid}; data: {result.data_status}")


if __name__ == "__main__":
    show("Normal planning run")
    show(
        "Charger-failure replan",
        {"type": "charger_failure", "start_slot": 12, "end_slot": 18, "unavailable_chargers": 1},
    )
