"""Tariff validation and explicit cache-first refresh flow.

Network fetching is intentionally injected by the caller.  The engine never
calls the network; an unavailable or invalid refresh returns the last known
cache with a clear status instead of inventing a price.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from live.cache import provenance_errors, read_json, write_cache


def validate_tariff(payload: dict[str, Any], expected_slots: int = 48) -> list[str]:
    errors = provenance_errors(payload)
    prices = payload.get("slot_prices")
    if not isinstance(prices, list) or len(prices) != expected_slots:
        errors.append(f"Tariff must contain exactly {expected_slots} slot prices.")
        return errors
    if any(not isinstance(price, (int, float)) or not 0 < price < 100 for price in prices):
        errors.append("Tariff prices must be numeric values between 0 and 100.")
    return errors


def refresh_tariff(
    cache_path: Path | str,
    fetcher: Callable[[], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], str]:
    """Return a validated refresh or the cache and an honest provenance status."""

    cached = read_json(cache_path)
    if fetcher is None:
        return cached, "cached: no refresh source configured"
    try:
        candidate = fetcher()
    except Exception as error:  # Boundary: refresh failures never break planning.
        return cached, f"cached: refresh failed ({error.__class__.__name__})"
    errors = validate_tariff(candidate, len(cached["slot_prices"]))
    if errors:
        return cached, "cached: refresh rejected (" + "; ".join(errors) + ")"
    candidate = dict(candidate)
    candidate["validation_status"] = "verified-by-rule"
    write_cache(cache_path, candidate)
    return candidate, "refreshed: verified-by-rule"
