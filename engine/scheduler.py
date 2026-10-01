"""Deterministic, slot-based fleet charging scheduler.

The scheduler is intentionally independent from the checker.  It first assigns
the tightest vehicle windows, then ranks each available slot by the requested
cost, availability, and battery-health priorities.  A final partial slot is
allowed because the configured chargers can throttle below their mode maximum.
"""

from __future__ import annotations

from collections import defaultdict
from math import ceil

from engine.energy import calculate_all_energy_needs
from engine.schemas import Assignment, ObjectiveWeights, PlanningInput, Schedule


def _candidate_score(
    *,
    slot: int,
    return_slot: int,
    departure_slot: int,
    price: float,
    max_price: float,
    is_fast: bool,
    fast_penalty: float,
    weights: ObjectiveWeights,
) -> tuple[float, int]:
    """Return a lower-is-better slot score and a stable slot tie-breaker."""

    window = max(1, departure_slot - return_slot)
    relative_time = (slot - return_slot) / window
    cost_component = weights.cost * (price / max_price)
    # Availability-weighted schedules prefer earlier slots and a wider buffer
    # before departure. Cost/health schedules can wait for cheap slots.
    availability_component = weights.availability * relative_time
    health_component = weights.health * fast_penalty if is_fast else 0.0
    return (cost_component + availability_component + health_component, slot)


def _choose_mode(
    *,
    remaining_kwh: float,
    free_slots: int,
    planning_input: PlanningInput,
    weights: ObjectiveWeights,
) -> str:
    modes = planning_input.chargers.modes
    standard_capacity = modes["standard"].maximum_energy_kwh(
        planning_input.chargers.slot_minutes
    )
    standard_slots_needed = ceil(remaining_kwh / standard_capacity)
    # Fast charging is reserved for narrow windows, or a deliberately
    # availability-first strategy. It is otherwise avoided for battery health.
    if standard_slots_needed > free_slots:
        return "fast"
    if weights.availability > max(weights.cost, weights.health):
        return "fast"
    return "standard"


def optimize_schedule(
    planning_input: PlanningInput,
    weights: ObjectiveWeights | None = None,
    *,
    strategy: str = "balanced",
) -> Schedule:
    """Build a deterministic feasible-first schedule with explicit shortfall.

    The result is never assumed valid by callers; it must be passed to
    :func:`engine.checker.check_schedule` before presentation or approval.
    """

    weights = (weights or ObjectiveWeights()).normalized()
    chargers = planning_input.chargers
    needs = calculate_all_energy_needs(planning_input.vehicles, planning_input.routes)
    usage_by_slot: dict[int, int] = defaultdict(int)
    assigned_slots_by_vehicle: dict[str, set[int]] = defaultdict(set)
    assignments: list[Assignment] = []
    delivered: dict[str, float] = {vehicle.vehicle_id: 0.0 for vehicle in planning_input.vehicles}
    max_price = max(planning_input.tariff.slot_prices)

    def tightness(vehicle_id: str) -> tuple[float, int, str]:
        vehicle = next(item for item in planning_input.vehicles if item.vehicle_id == vehicle_id)
        window = max(1, vehicle.departure_slot - vehicle.return_slot)
        standard_energy = chargers.modes["standard"].maximum_energy_kwh(chargers.slot_minutes)
        required_slots = needs[vehicle_id].required_charge_kwh / standard_energy
        return (-(required_slots / window), vehicle.departure_slot, vehicle_id)

    # Tightest windows are assigned first so late-departing vehicles cannot
    # silently consume the only slots usable by a critical return.
    for vehicle in sorted(planning_input.vehicles, key=lambda item: tightness(item.vehicle_id)):
        remaining = needs[vehicle.vehicle_id].required_charge_kwh
        while remaining > 1e-9:
            free_slots = [
                slot
                for slot in range(vehicle.return_slot, vehicle.departure_slot)
                if usage_by_slot[slot] < chargers.capacity_at(slot)
                and slot not in assigned_slots_by_vehicle[vehicle.vehicle_id]
            ]
            if not free_slots:
                break

            mode_name = _choose_mode(
                remaining_kwh=remaining,
                free_slots=len(free_slots),
                planning_input=planning_input,
                weights=weights,
            )
            mode = chargers.modes[mode_name]
            ranked_slots = sorted(
                free_slots,
                key=lambda slot: _candidate_score(
                    slot=slot,
                    return_slot=vehicle.return_slot,
                    departure_slot=vehicle.departure_slot,
                    price=planning_input.tariff.slot_prices[slot],
                    max_price=max_price,
                    is_fast=mode_name == "fast",
                    fast_penalty=mode.health_penalty,
                    weights=weights,
                ),
            )
            slot = ranked_slots[0]
            maximum = mode.maximum_energy_kwh(chargers.slot_minutes)
            energy = min(maximum, remaining)
            assignments.append(
                Assignment(
                    vehicle_id=vehicle.vehicle_id,
                    slot=slot,
                    mode=mode_name,
                    energy_kwh=round(energy, 3),
                )
            )
            usage_by_slot[slot] += 1
            assigned_slots_by_vehicle[vehicle.vehicle_id].add(slot)
            delivered[vehicle.vehicle_id] = round(delivered[vehicle.vehicle_id] + energy, 3)
            remaining = round(max(0.0, remaining - energy), 9)

    unmet = {
        vehicle_id: round(max(0.0, needs[vehicle_id].required_charge_kwh - amount), 3)
        for vehicle_id, amount in delivered.items()
    }
    energy_cost = sum(
        assignment.energy_kwh * planning_input.tariff.slot_prices[assignment.slot]
        for assignment in assignments
    )
    health_cost = sum(
        assignment.energy_kwh
        / chargers.modes[assignment.mode].maximum_energy_kwh(chargers.slot_minutes)
        * chargers.modes[assignment.mode].health_penalty
        for assignment in assignments
    )
    availability_cost = sum(unmet.values())
    objective = {
        "energy_cost": round(energy_cost, 2),
        "health_penalty": round(health_cost, 3),
        "unmet_energy_kwh": round(availability_cost, 3),
        "weighted_score": round(
            weights.cost * energy_cost
            + weights.health * health_cost
            + weights.availability * availability_cost * 100,
            3,
        ),
    }
    notes = []
    if availability_cost:
        notes.append("The schedule is infeasible at the requested targets; shortfalls are explicit.")
    else:
        notes.append("All configured departure-energy targets are scheduled.")
    return Schedule(
        assignments=sorted(assignments, key=lambda item: (item.slot, item.vehicle_id)),
        required_energy_kwh={key: value.required_charge_kwh for key, value in needs.items()},
        delivered_energy_kwh=delivered,
        unmet_energy_kwh=unmet,
        objective=objective,
        strategy=strategy,
        notes=notes,
    )


def charge_immediately_baseline(planning_input: PlanningInput) -> Schedule:
    """A readiness-first baseline used for reproducible cost comparisons."""

    return optimize_schedule(
        planning_input,
        ObjectiveWeights(cost=0, availability=100, health=0),
        strategy="charge-immediately baseline",
    )


def greedy_cost_baseline(planning_input: PlanningInput) -> Schedule:
    """A simple cheap-slot baseline used to report improvement transparently."""

    return optimize_schedule(
        planning_input,
        ObjectiveWeights(cost=100, availability=0, health=0),
        strategy="greedy cheapest-slot baseline",
    )
