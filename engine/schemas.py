"""Typed domain objects for the deterministic charging engine.

The schemas deliberately contain no UI or agent concerns.  This keeps the
optimizer and independent checker usable from tests, scripts, and the app.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    route_id: str
    battery_capacity_kwh: float
    soc_percent: float
    soh_percent: float
    target_soc_percent: float
    reserve_percent: float
    max_soc_percent: float
    return_slot: int
    departure_slot: int
    temperature_c: float


@dataclass(frozen=True)
class Route:
    route_id: str
    distance_km: float
    energy_per_km_kwh: float

    @property
    def planned_energy_kwh(self) -> float:
        return self.distance_km * self.energy_per_km_kwh


@dataclass(frozen=True)
class ChargingMode:
    name: str
    power_kw: float
    efficiency: float
    health_penalty: float

    def maximum_energy_kwh(self, slot_minutes: int) -> float:
        return self.power_kw * (slot_minutes / 60) * self.efficiency


@dataclass(frozen=True)
class ChargerConfig:
    slot_minutes: int
    horizon_slots: int
    charger_capacity: int
    modes: dict[str, ChargingMode]
    capacity_overrides: dict[int, int] = field(default_factory=dict)

    def capacity_at(self, slot: int) -> int:
        return self.capacity_overrides.get(slot, self.charger_capacity)


@dataclass(frozen=True)
class Tariff:
    slot_prices: tuple[float, ...]
    source: str
    fetched_at: str
    validation_status: str
    currency: str = "INR"
    unit: str = "INR/kWh"


@dataclass(frozen=True)
class ObjectiveWeights:
    cost: int = 50
    availability: int = 30
    health: int = 20

    def normalized(self) -> "ObjectiveWeights":
        total = self.cost + self.availability + self.health
        if total <= 0:
            return ObjectiveWeights(34, 33, 33)
        return ObjectiveWeights(
            cost=round(self.cost * 100 / total),
            availability=round(self.availability * 100 / total),
            health=round(self.health * 100 / total),
        )


@dataclass(frozen=True)
class Assignment:
    vehicle_id: str
    slot: int
    mode: str
    energy_kwh: float


@dataclass
class Schedule:
    assignments: list[Assignment]
    required_energy_kwh: dict[str, float]
    delivered_energy_kwh: dict[str, float]
    unmet_energy_kwh: dict[str, float]
    objective: dict[str, float]
    strategy: str
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "assignments": [asdict(item) for item in self.assignments],
            "required_energy_kwh": self.required_energy_kwh,
            "delivered_energy_kwh": self.delivered_energy_kwh,
            "unmet_energy_kwh": self.unmet_energy_kwh,
            "objective": self.objective,
            "strategy": self.strategy,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    vehicle_id: str | None = None
    slot: int | None = None


@dataclass
class CheckResult:
    valid: bool
    violations: list[Violation]
    delivered_energy_kwh: dict[str, float]
    cost: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "violations": [asdict(item) for item in self.violations],
            "delivered_energy_kwh": self.delivered_energy_kwh,
            "cost": self.cost,
        }


@dataclass(frozen=True)
class PlanningInput:
    vehicles: tuple[Vehicle, ...]
    routes: dict[str, Route]
    chargers: ChargerConfig
    tariff: Tariff
