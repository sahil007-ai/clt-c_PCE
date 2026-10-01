"""The only interface a coordinator uses to access deterministic operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from engine.checker import check_schedule
from engine.events import apply_event
from engine.schemas import CheckResult, ObjectiveWeights, PlanningInput, Schedule
from engine.scheduler import optimize_schedule


@dataclass(frozen=True)
class ToolProposal:
    name: str
    weights: ObjectiveWeights
    schedule: Schedule
    check: CheckResult


class EngineTools:
    """Tool boundary that keeps all calculation outside the coordinator."""

    def __init__(self, planning_input: PlanningInput):
        self.planning_input = planning_input

    def propose(self, name: str, weights: ObjectiveWeights) -> ToolProposal:
        schedule = optimize_schedule(self.planning_input, weights, strategy=name)
        return ToolProposal(name, weights.normalized(), schedule, check_schedule(self.planning_input, schedule))

    def simulate_event(self, event: dict) -> "EngineTools":
        return EngineTools(apply_event(self.planning_input, event))


def record_approval(
    schedule: Schedule,
    *,
    operator: str,
    destination: Path | str,
) -> Path:
    """Append an explicit local approval record; never contacts charging gear."""

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "approved_at": datetime.now(UTC).isoformat(),
        "operator": operator,
        "strategy": schedule.strategy,
        "schedule": schedule.as_dict(),
        "execution": "not sent to hardware",
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return target
