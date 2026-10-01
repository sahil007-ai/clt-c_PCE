"""Deterministic disruption transformations used before targeted replanning."""

from __future__ import annotations

from dataclasses import replace

from engine.schemas import ChargerConfig, PlanningInput, Tariff, Vehicle


def apply_event(planning_input: PlanningInput, event: dict) -> PlanningInput:
    """Return a new input snapshot for a supported disruption event.

    Events never mutate the original snapshot, preserving an auditable before
    and after state. Missing battery data is deliberately rejected rather than
    guessed.
    """

    event_type = event.get("type")
    if event_type == "charger_failure":
        start = int(event["start_slot"])
        end = int(event["end_slot"])
        unavailable = int(event.get("unavailable_chargers", 1))
        overrides = dict(planning_input.chargers.capacity_overrides)
        for slot in range(start, end):
            overrides[slot] = max(0, planning_input.chargers.capacity_at(slot) - unavailable)
        chargers = replace(planning_input.chargers, capacity_overrides=overrides)
        return replace(planning_input, chargers=chargers)

    if event_type == "late_return":
        vehicle_id = event["vehicle_id"]
        new_return_slot = int(event["return_slot"])
        vehicles = tuple(
            replace(vehicle, return_slot=new_return_slot)
            if vehicle.vehicle_id == vehicle_id
            else vehicle
            for vehicle in planning_input.vehicles
        )
        if all(vehicle.vehicle_id != vehicle_id for vehicle in planning_input.vehicles):
            raise ValueError(f"Unknown vehicle for late-return event: {vehicle_id}")
        return replace(planning_input, vehicles=vehicles)

    if event_type == "price_spike":
        start = int(event["start_slot"])
        end = int(event["end_slot"])
        price = float(event["price"])
        prices = list(planning_input.tariff.slot_prices)
        prices[start:end] = [price] * len(prices[start:end])
        tariff = Tariff(
            slot_prices=tuple(prices),
            source=planning_input.tariff.source,
            fetched_at=planning_input.tariff.fetched_at,
            validation_status="event-adjusted-fixture",
            currency=planning_input.tariff.currency,
            unit=planning_input.tariff.unit,
        )
        return replace(planning_input, tariff=tariff)

    if event_type == "missing_battery_data":
        raise ValueError(
            "Battery data is missing. Replanning is blocked until an operator supplies a verified value."
        )
    raise ValueError(f"Unsupported event type: {event_type}")
