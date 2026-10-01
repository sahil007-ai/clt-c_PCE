"""Load versioned fixture/cache data into the typed planning input."""

from __future__ import annotations

import json
from pathlib import Path

from engine.schemas import (
    ChargerConfig,
    ChargingMode,
    PlanningInput,
    Route,
    Tariff,
    Vehicle,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_planning_input(
    data_dir: Path | str = DEFAULT_DATA_DIR, *, use_cache: bool = True
) -> PlanningInput:
    data_dir = Path(data_dir)
    fleet_payload = _read_json(data_dir / "fleet.json")
    routes_payload = _read_json(data_dir / "routes.json")
    chargers_payload = _read_json(data_dir / "chargers.json")
    tariff_path = data_dir / "cache" / "tariffs.json" if use_cache else data_dir / "tariffs.json"
    tariff_payload = _read_json(tariff_path)

    modes = {
        name: ChargingMode(name=name, **values)
        for name, values in chargers_payload["modes"].items()
    }
    chargers = ChargerConfig(
        slot_minutes=chargers_payload["slot_minutes"],
        horizon_slots=chargers_payload["horizon_slots"],
        charger_capacity=chargers_payload["charger_capacity"],
        modes=modes,
    )
    routes = {
        item["route_id"]: Route(**item) for item in routes_payload["routes"]
    }
    vehicles = tuple(Vehicle(**item) for item in fleet_payload["vehicles"])
    tariff = Tariff(
        slot_prices=tuple(float(price) for price in tariff_payload["slot_prices"]),
        source=tariff_payload["source"],
        fetched_at=tariff_payload["fetched_at"],
        validation_status=tariff_payload["validation_status"],
        currency=tariff_payload.get("currency", "INR"),
        unit=tariff_payload.get("unit", "INR/kWh"),
    )

    if len(tariff.slot_prices) != chargers.horizon_slots:
        raise ValueError("Tariff slot count must match the charger planning horizon.")
    return PlanningInput(vehicles=vehicles, routes=routes, chargers=chargers, tariff=tariff)
