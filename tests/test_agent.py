from __future__ import annotations

import unittest

from agent.graph import coordinate_plan
from engine.generate import load_planning_input
from engine.schemas import ObjectiveWeights


class AgentTests(unittest.TestCase):
    def test_coordinator_selects_a_checked_and_grounded_proposal(self) -> None:
        result = coordinate_plan(load_planning_input(), ObjectiveWeights(cost=60, availability=30, health=10))
        self.assertTrue(result.selected.check.valid)
        self.assertTrue(result.explanation_is_grounded)

    def test_missing_battery_data_is_explicitly_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "Battery data is missing"):
            coordinate_plan(load_planning_input(), event={"type": "missing_battery_data"})


if __name__ == "__main__":
    unittest.main()
