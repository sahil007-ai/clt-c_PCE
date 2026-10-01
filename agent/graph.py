"""Deterministic multi-objective coordinator built on checked tool proposals."""

from __future__ import annotations

from dataclasses import dataclass

from agent.grounding import verify_numeric_grounding
from agent.tools import EngineTools, ToolProposal
from engine.schemas import ObjectiveWeights, PlanningInput


SPECIALIST_WEIGHTS = {
    "cost": ObjectiveWeights(cost=100, availability=0, health=0),
    "availability": ObjectiveWeights(cost=0, availability=100, health=0),
    "battery health": ObjectiveWeights(cost=0, availability=0, health=100),
}


@dataclass(frozen=True)
class CoordinationResult:
    planning_input: PlanningInput
    proposals: tuple[ToolProposal, ...]
    selected: ToolProposal
    explanation: str
    explanation_is_grounded: bool
    data_status: str


def _selection_score(proposal: ToolProposal, weights: ObjectiveWeights, minima: dict[str, float]) -> float:
    objective = proposal.schedule.objective
    # Unmet energy is deliberately multiplied enough to dominate a small cost
    # advantage when the operator values availability.
    return (
        weights.cost * objective["energy_cost"] / minima["energy_cost"]
        + weights.health * (1 + objective["health_penalty"])
        + weights.availability * objective["unmet_energy_kwh"] * 100
    )


def coordinate_plan(
    planning_input: PlanningInput,
    weights: ObjectiveWeights | None = None,
    *,
    event: dict | None = None,
) -> CoordinationResult:
    """Ask specialist tools for checked proposals and select a transparent plan."""

    tools = EngineTools(planning_input)
    if event is not None:
        tools = tools.simulate_event(event)
    requested_weights = (weights or ObjectiveWeights()).normalized()
    proposals = [
        tools.propose(name, specialist_weights)
        for name, specialist_weights in SPECIALIST_WEIGHTS.items()
    ]
    proposals.append(tools.propose("operator weighted", requested_weights))
    valid = [proposal for proposal in proposals if proposal.check.valid]
    candidates = valid or proposals
    minima = {
        "energy_cost": max(0.01, min(item.schedule.objective["energy_cost"] for item in candidates)),
    }
    selected = min(
        candidates,
        key=lambda proposal: _selection_score(proposal, requested_weights, minima),
    )
    total_vehicles = len(tools.planning_input.vehicles)
    unmet = selected.schedule.objective["unmet_energy_kwh"]
    ready = sum(1 for amount in selected.schedule.unmet_energy_kwh.values() if amount <= 0)
    energy = sum(selected.schedule.delivered_energy_kwh.values())
    cost = selected.check.cost
    # Keep facts at the same precision used by the rendered explanation.
    facts = (total_vehicles, ready, round(unmet, 1), round(energy, 1), round(cost, 2))
    if selected.check.valid:
        explanation = (
            f"The independent verifier accepted the {selected.name} proposal. It schedules "
            f"{energy:.1f} kWh for {ready} of {total_vehicles} vehicles at a calculated energy cost "
            f"of INR {cost:.2f}. Remaining unmet energy is {unmet:.1f} kWh. Human approval is still required."
        )
    else:
        explanation = (
            f"The proposed plan has {unmet:.1f} kWh of unmet energy across {total_vehicles} vehicles. "
            "The verifier rejected it, so the coordinator requires an operator decision before approval."
        )
    return CoordinationResult(
        planning_input=tools.planning_input,
        proposals=tuple(proposals),
        selected=selected,
        explanation=explanation,
        explanation_is_grounded=verify_numeric_grounding(explanation, facts),
        data_status=tools.planning_input.tariff.validation_status,
    )
