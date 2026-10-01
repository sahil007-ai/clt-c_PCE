"""Baseline helpers used by the evaluation runner."""

from engine.checker import check_schedule
from engine.schemas import PlanningInput
from engine.scheduler import charge_immediately_baseline, greedy_cost_baseline


def baseline_results(planning_input: PlanningInput) -> dict[str, float | bool]:
    immediate = charge_immediately_baseline(planning_input)
    greedy = greedy_cost_baseline(planning_input)
    immediate_check = check_schedule(planning_input, immediate)
    greedy_check = check_schedule(planning_input, greedy)
    return {
        "charge_immediately_cost": immediate_check.cost,
        "charge_immediately_valid": immediate_check.valid,
        "greedy_cost": greedy_check.cost,
        "greedy_valid": greedy_check.valid,
    }
