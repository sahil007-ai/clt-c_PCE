"""CLI that reports cache-first refresh state without making implicit requests."""

from __future__ import annotations

from engine.generate import DEFAULT_DATA_DIR
from live.routes import refresh_routes
from live.tariffs import refresh_tariff


def main() -> None:
    _, tariff_status = refresh_tariff(DEFAULT_DATA_DIR / "cache" / "tariffs.json")
    _, route_status = refresh_routes(DEFAULT_DATA_DIR / "cache" / "routes.json")
    print(f"Tariff: {tariff_status}")
    print(f"Routes: {route_status}")


if __name__ == "__main__":
    main()
