"""Unit tests for the grounded multi-agent operations copilot."""

from __future__ import annotations

import unittest

from agent.copilot import (
    BatteryHealthReviewerAgent,
    DataQualitySafetyReviewerAgent,
    OperatorBriefingAgent,
    PlannerAgent,
    ScenarioAnalystAgent,
    run_operations_copilot,
)
from agent.graph import coordinate_plan
from engine.generate import load_planning_input
from engine.schemas import ObjectiveWeights


class CopilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planning_input = load_planning_input()
        self.weights = ObjectiveWeights(cost=60, availability=30, health=10)
        self.normal_result = coordinate_plan(self.planning_input, self.weights)

    def test_planner_agent_grounding(self) -> None:
        report = PlannerAgent().analyze(self.normal_result)
        self.assertEqual(report.role, "Planner Specialist")
        self.assertTrue(report.is_grounded)
        self.assertEqual(report.status, "verified")

    def test_scenario_analyst_normal_and_disruptions(self) -> None:
        analyst = ScenarioAnalystAgent()

        # Normal operation
        normal_rep = analyst.analyze(self.normal_result)
        self.assertTrue(normal_rep.is_grounded)
        self.assertEqual(normal_rep.status, "verified")

        # Charger failure
        cf_event = {"type": "charger_failure", "start_slot": 12, "end_slot": 18, "unavailable_chargers": 1}
        cf_result = coordinate_plan(self.planning_input, self.weights, event=cf_event)
        cf_rep = analyst.analyze(cf_result, event=cf_event)
        self.assertTrue(cf_rep.is_grounded)

        # Price spike
        ps_event = {"type": "price_spike", "start_slot": 16, "end_slot": 20, "price": 12.0}
        ps_result = coordinate_plan(self.planning_input, self.weights, event=ps_event)
        ps_rep = analyst.analyze(ps_result, event=ps_event)
        self.assertTrue(ps_rep.is_grounded)

    def test_battery_reviewer_thermal_and_modes(self) -> None:
        report = BatteryHealthReviewerAgent().analyze(self.normal_result)
        self.assertEqual(report.role, "Battery Health Reviewer")
        self.assertTrue(report.is_grounded)
        self.assertIn("SOH", report.details[0])

    def test_safety_reviewer_asserts_boundary_and_provenance(self) -> None:
        report = DataQualitySafetyReviewerAgent().analyze(self.normal_result)
        self.assertEqual(report.role, "Data Quality & Safety Auditor")
        self.assertTrue(report.is_grounded)
        self.assertEqual(report.status, "verified")
        self.assertTrue(any("hardware command" in d.lower() for d in report.details))

    def test_operator_briefing_synthesis(self) -> None:
        briefing = run_operations_copilot(self.normal_result)
        self.assertEqual(briefing.overall_status, "ready_for_approval")
        self.assertTrue(briefing.operator_briefing.is_grounded)
        self.assertTrue(briefing.planner.is_grounded)
        self.assertTrue(briefing.scenario_analyst.is_grounded)
        self.assertTrue(briefing.battery_reviewer.is_grounded)
        self.assertTrue(briefing.safety_reviewer.is_grounded)


if __name__ == "__main__":
    unittest.main()
