"""Energy-need calculations used by the scheduler and checker.

All calculations are deterministic and unit-tested.  An agent may request the
result, but never re-implements the arithmetic in generated text.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.schemas import Route, Vehicle


@dataclass(frozen=True)
class EnergyNeed:
    vehicle_id: str
    route_energy_kwh: float
    reserve_energy_kwh: float
    target_energy_kwh: float
    required_charge_kwh: float
    maximum_charge_kwh: float


def calculate_energy_need(vehicle: Vehicle, route: Route) -> EnergyNeed:
    """Return the charge needed to meet the configured departure target.

    The target must also cover route energy plus reserve.  This means an input
    target that is too low is made safe, while charging still never exceeds the
    configured maximum state of charge.
    """

    current_energy = vehicle.battery_capacity_kwh * vehicle.soc_percent / 100
    reserve_energy = vehicle.battery_capacity_kwh * vehicle.reserve_percent / 100
    route_energy = route.planned_energy_kwh
    safe_departure_energy = route_energy + reserve_energy
    configured_target_energy = (
        vehicle.battery_capacity_kwh * vehicle.target_soc_percent / 100
    )
    maximum_energy = vehicle.battery_capacity_kwh * vehicle.max_soc_percent / 100
    target_energy = min(max(configured_target_energy, safe_departure_energy), maximum_energy)

    return EnergyNeed(
        vehicle_id=vehicle.vehicle_id,
        route_energy_kwh=round(route_energy, 3),
        reserve_energy_kwh=round(reserve_energy, 3),
        target_energy_kwh=round(target_energy, 3),
        required_charge_kwh=round(max(0.0, target_energy - current_energy), 3),
        maximum_charge_kwh=round(max(0.0, maximum_energy - current_energy), 3),
    )


def calculate_all_energy_needs(
    vehicles: tuple[Vehicle, ...], routes: dict[str, Route]
) -> dict[str, EnergyNeed]:
    return {
        vehicle.vehicle_id: calculate_energy_need(vehicle, routes[vehicle.route_id])
        for vehicle in vehicles
    }
