from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from engine.generate import DEFAULT_DATA_DIR
from live.cache import read_json, write_cache
from live.routes import refresh_routes, validate_routes
from live.tariffs import refresh_tariff, validate_tariff


class LiveValidationTests(unittest.TestCase):
    def test_tariff_requires_complete_plausible_slots_and_provenance(self) -> None:
        payload = read_json(DEFAULT_DATA_DIR / "cache" / "tariffs.json")
        self.assertEqual(validate_tariff(payload), [])
        payload["slot_prices"] = payload["slot_prices"][:-1]
        self.assertTrue(validate_tariff(payload))

    def test_rejected_tariff_refresh_falls_back_to_cache(self) -> None:
        source = read_json(DEFAULT_DATA_DIR / "cache" / "tariffs.json")
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "tariffs.json"
            write_cache(cache, source)
            result, status = refresh_tariff(cache, lambda: {"slot_prices": [1]})
        self.assertEqual(result["slot_prices"], source["slot_prices"])
        self.assertTrue(status.startswith("cached: refresh rejected"))

    def test_routes_validate_and_reject_invalid_refresh(self) -> None:
        payload = read_json(DEFAULT_DATA_DIR / "cache" / "routes.json")
        self.assertEqual(validate_routes(payload), [])
        invalid = copy.deepcopy(payload)
        invalid["routes"][0]["distance_km"] = 0
        self.assertTrue(validate_routes(invalid))
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = Path(temp_dir) / "routes.json"
            write_cache(cache, payload)
            result, status = refresh_routes(cache, lambda: invalid)
        self.assertEqual(result["routes"], payload["routes"])
        self.assertTrue(status.startswith("cached: refresh rejected"))


if __name__ == "__main__":
    unittest.main()
