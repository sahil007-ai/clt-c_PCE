"""Cache helpers with explicit provenance requirements."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def read_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_cache(path: Path | str, payload: dict[str, Any]) -> dict[str, Any]:
    """Write a validated payload and stamp its cache time if not provided."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload.setdefault("fetched_at", datetime.now(UTC).isoformat())
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def provenance_errors(payload: dict[str, Any]) -> list[str]:
    required = ("source", "fetched_at", "validation_status")
    return [f"Missing provenance field: {field}" for field in required if not payload.get(field)]
