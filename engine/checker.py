"""Independent schedule verifier.

This module deliberately does not import the scheduler.  It recomputes vehicle
energy needs and all constraint checks directly from raw input and assignments.
"""

from __future__ import annotations

from collections import defaultdict

from engine.energy import calculate_all_energy_needs
from engine.schemas import Assignment, CheckResult, PlanningInput, Schedule, Violation


def check_schedule(
    planning_input: PlanningInput, schedule: Schedule | list[Assignment]
) -> CheckResult:
    assignments = schedule.assignments if isinstance(schedule, Schedule) else schedule
    vehicles = {vehicle.vehicle_id: vehicle for vehicle in planning_input.vehicles}
    chargers = planning_input.chargers
    delivered: dict[str, float] = defaultdict(float)
    usage_by_slot: dict[int, int] = defaultdict(int)
    seen_vehicle_slots: set[tuple[str, int]] = set()
    violations: list[Violation] = []
    cost = 0.0

    for assignment in assignments:
        vehicle = vehicles.get(assignment.vehicle_id)
        if vehicle is None:
            violations.append(Violation("unknown_vehicle", "Assignment names an unknown vehicle.", assignment.vehicle_id, assignment.slot))
            continue
        if assignment.slot < 0 or assignment.slot >= chargers.horizon_slots:
            violations.append(Violation("slot_out_of_range", "Assignment slot is outside the planning horizon.", assignment.vehicle_id, assignment.slot))
            continue
        if not vehicle.return_slot <= assignment.slot < vehicle.departure_slot:
            violations.append(Violation("outside_parking_window", "Vehicle is assigned outside its parking window.", assignment.vehicle_id, assignment.slot))
        if assignment.mode not in chargers.modes:
            violations.append(Violation("unknown_mode", "Assignment names an unknown charging mode.", assignment.vehicle_id, assignment.slot))
            continue
        maximum_energy = chargers.modes[assignment.mode].maximum_energy_kwh(chargers.slot_minutes)
        if not 0 < assignment.energy_kwh <= maximum_energy + 1e-9:
            violations.append(Violation("invalid_energy", "Assignment energy must be positive and not exceed the mode maximum.", assignment.vehicle_id, assignment.slot))
        vehicle_slot = (assignment.vehicle_id, assignment.slot)
        if vehicle_slot in seen_vehicle_slots:
            violations.append(Violation("multiple_modes", "Vehicle has more than one assignment in a slot.", assignment.vehicle_id, assignment.slot))
        seen_vehicle_slots.add(vehicle_slot)
        usage_by_slot[assignment.slot] += 1
        delivered[assignment.vehicle_id] += assignment.energy_kwh
        cost += assignment.energy_kwh * planning_input.tariff.slot_prices[assignment.slot]

    for slot, usage in usage_by_slot.items():
        if usage > chargers.capacity_at(slot):
            violations.append(Violation("charger_capacity", "Assigned chargers exceed slot capacity.", slot=slot))

    needs = calculate_all_energy_needs(planning_input.vehicles, planning_input.routes)
    for vehicle in planning_input.vehicles:
        amount = delivered[vehicle.vehicle_id]
        need = needs[vehicle.vehicle_id]
        if amount + 1e-9 < need.required_charge_kwh:
            violations.append(Violation("unmet_energy", "Vehicle has insufficient scheduled energy for its departure target.", vehicle.vehicle_id))
        if amount > need.maximum_charge_kwh + 1e-9:
            violations.append(Violation("battery_ceiling", "Scheduled energy exceeds the configured battery ceiling.", vehicle.vehicle_id))

    return CheckResult(
        valid=not violations,
        violations=violations,
        delivered_energy_kwh={key: round(value, 3) for key, value in delivered.items()},
        cost=round(cost, 2),
    )
