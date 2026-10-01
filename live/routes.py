"""Route-matrix validation and cache-first refresh flow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from live.cache import provenance_errors, read_json, write_cache


def validate_routes(payload: dict[str, Any]) -> list[str]:
    errors = provenance_errors(payload)
    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes:
        return errors + ["Route payload must contain at least one route."]
    for route in routes:
        if not route.get("route_id"):
            errors.append("Route is missing route_id.")
        if not isinstance(route.get("distance_km"), (int, float)) or route["distance_km"] <= 0:
            errors.append("Route distance must be positive.")
        if not isinstance(route.get("duration_minutes"), (int, float)) or route["duration_minutes"] <= 0:
            errors.append("Route duration must be positive.")
    return errors


def refresh_routes(
    cache_path: Path | str,
    fetcher: Callable[[], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], str]:
    cached = read_json(cache_path)
    if fetcher is None:
        return cached, "cached: no refresh source configured"
    try:
        candidate = fetcher()
    except Exception as error:
        return cached, f"cached: refresh failed ({error.__class__.__name__})"
    errors = validate_routes(candidate)
    if errors:
        return cached, "cached: refresh rejected (" + "; ".join(errors) + ")"
    candidate = dict(candidate)
    candidate["validation_status"] = "verified-by-rule"
    write_cache(cache_path, candidate)
    return candidate, "refreshed: verified-by-rule"
