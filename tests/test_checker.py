from __future__ import annotations

import unittest

from engine.checker import check_schedule
from engine.generate import load_planning_input
from engine.schemas import Assignment


class CheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planning_input = load_planning_input()

    def test_checker_catches_assignment_outside_parking_window(self) -> None:
        result = check_schedule(
            self.planning_input,
            [Assignment("EV-103", 0, "standard", 2)],
        )
        self.assertIn("outside_parking_window", [item.code for item in result.violations])

    def test_checker_catches_capacity_and_duplicate_vehicle_slot(self) -> None:
        assignments = [
            Assignment("EV-101", 4, "standard", 2),
            Assignment("EV-102", 4, "standard", 2),
            Assignment("EV-104", 4, "standard", 2),
            Assignment("EV-108", 4, "standard", 2),
            Assignment("EV-110", 4, "standard", 2),
            Assignment("EV-101", 4, "fast", 4),
        ]
        result = check_schedule(self.planning_input, assignments)
        codes = [item.code for item in result.violations]
        self.assertIn("multiple_modes", codes)
        self.assertIn("charger_capacity", codes)

    def test_checker_catches_battery_ceiling(self) -> None:
        assignments = [
            Assignment("EV-102", slot, "fast", 4)
            for slot in range(0, 16)
        ]
        result = check_schedule(self.planning_input, assignments)
        self.assertIn("battery_ceiling", [item.code for item in result.violations])


if __name__ == "__main__":
    unittest.main()
