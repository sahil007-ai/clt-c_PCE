from __future__ import annotations

import unittest

from engine.checker import check_schedule
from engine.energy import calculate_all_energy_needs
from engine.generate import load_planning_input
from engine.scheduler import charge_immediately_baseline, greedy_cost_baseline, optimize_schedule


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planning_input = load_planning_input()

    def test_energy_need_never_exceeds_configured_ceiling(self) -> None:
        needs = calculate_all_energy_needs(self.planning_input.vehicles, self.planning_input.routes)
        for need in needs.values():
            self.assertLessEqual(need.required_charge_kwh, need.maximum_charge_kwh)

    def test_operator_weighted_schedule_is_verifiable(self) -> None:
        schedule = optimize_schedule(self.planning_input)
        checked = check_schedule(self.planning_input, schedule)
        self.assertTrue(checked.valid, [violation.message for violation in checked.violations])
        self.assertEqual(sum(schedule.unmet_energy_kwh.values()), 0)

    def test_baselines_are_checked_before_comparison(self) -> None:
        for schedule in (
            charge_immediately_baseline(self.planning_input),
            greedy_cost_baseline(self.planning_input),
        ):
            self.assertTrue(check_schedule(self.planning_input, schedule).valid)


if __name__ == "__main__":
    unittest.main()
