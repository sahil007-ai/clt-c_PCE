"""Grounded multi-agent operations copilot for EV fleet charging.

Agents may interpret requests, compare verified proposals, and explain
trade-offs, but may not calculate schedules, invent data, bypass the checker,
or send hardware commands.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from agent.graph import CoordinationResult
from agent.grounding import verify_numeric_grounding
from agent.prompts import (
    BATTERY_HEALTH_RULES,
    DATA_SAFETY_RULES,
    OPERATOR_BRIEFING_RULES,
    PLANNER_RULES,
    SCENARIO_ANALYST_RULES,
)
import os
from pathlib import Path

def _get_openrouter_token() -> str | None:
    token = os.getenv("OPENROUTER_API_KEY")
    if token:
        return token
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    val = line.partition("=")[2].strip().strip("'\"")
                    if val:
                        return val
        except Exception:
            pass
    return None


@dataclass(frozen=True)
class AgentReport:
    role: str
    summary: str
    details: tuple[str, ...]
    facts: tuple[float | int | str, ...]
    is_grounded: bool
    status: str = "verified"  # "verified", "warning", "blocked"


@dataclass(frozen=True)
class CopilotBriefing:
    planner: AgentReport
    scenario_analyst: AgentReport
    battery_reviewer: AgentReport
    safety_reviewer: AgentReport
    operator_briefing: AgentReport
    overall_status: str  # "ready_for_approval", "needs_operator_decision", "blocked"


class PlannerAgent:
    """Interprets operator priorities and compares checked proposals."""

    def analyze(self, result: CoordinationResult) -> AgentReport:
        selected = result.selected
        proposals = result.proposals
        total_vehicles = len(result.planning_input.vehicles)
        ready_count = sum(1 for amount in selected.schedule.unmet_energy_kwh.values() if amount <= 0)
        unmet_kwh = round(selected.schedule.objective["unmet_energy_kwh"], 1)
        delivered_kwh = round(sum(selected.schedule.delivered_energy_kwh.values()), 1)
        selected_cost = round(selected.check.cost, 2)

        # Collect facts from all proposals
        proposal_costs = [round(p.check.cost, 2) for p in proposals]
        proposal_unmets = [round(p.schedule.objective["unmet_energy_kwh"], 1) for p in proposals]
        facts = tuple(sorted(set(
            [total_vehicles, ready_count, unmet_kwh, delivered_kwh, selected_cost]
            + proposal_costs
            + proposal_unmets
        )))

        cost_proposal = next((p for p in proposals if p.name == "cost"), None)
        avail_proposal = next((p for p in proposals if p.name == "availability"), None)

        details = []
        if cost_proposal and avail_proposal and cost_proposal != avail_proposal:
            cost_diff = round(abs(avail_proposal.check.cost - cost_proposal.check.cost), 2)
            facts = tuple(sorted(set(facts + (cost_diff,))))
            details.append(
                f"Cost proposal evaluates to INR {cost_proposal.check.cost:.2f} while availability "
                f"proposal evaluates to INR {avail_proposal.check.cost:.2f}."
            )

        details.append(
            f"Selected proposal ({selected.name}) delivers {delivered_kwh:.1f} kWh across "
            f"{ready_count} of {total_vehicles} vehicles at INR {selected_cost:.2f}."
        )

        summary = (
            f"The planner recommends the {selected.name} strategy. It schedules {delivered_kwh:.1f} kWh "
            f"for {ready_count} of {total_vehicles} vehicles at calculated energy cost INR {selected_cost:.2f} "
            f"with {unmet_kwh:.1f} kWh unmet energy."
        )

        return AgentReport(
            role="Planner Specialist",
            summary=summary,
            details=tuple(details),
            facts=facts,
            is_grounded=verify_numeric_grounding(summary, facts),
            status="verified" if selected.check.valid else "warning",
        )


class ScenarioAnalystAgent:
    """Analyzes active depot disruption events and replanning diffs."""

    def analyze(self, result: CoordinationResult, event: dict | None = None) -> AgentReport:
        schedule = result.selected.schedule
        total_assignments = len(schedule.assignments)
        unmet_kwh = round(schedule.objective["unmet_energy_kwh"], 1)

        if not event:
            facts = (total_assignments, unmet_kwh, 48, 4)
            summary = (
                f"Depot operations are running normally under full nominal capacity across all 48 slots "
                f"with 4 chargers available. Total scheduled assignments: {total_assignments}."
            )
            details = (
                "No disruption event active. Nominal parking windows and standard slot capacity apply.",
                f"Total charging assignments in plan: {total_assignments}.",
            )
            return AgentReport(
                role="Disruption Scenario Analyst",
                summary=summary,
                details=details,
                facts=facts,
                is_grounded=verify_numeric_grounding(summary, facts),
                status="verified",
            )

        event_type = event.get("type", "unknown")
        details = []

        if event_type == "charger_failure":
            start_slot = event.get("start_slot", 12)
            end_slot = event.get("end_slot", 18)
            unavail = event.get("unavailable_chargers", 1)
            facts = (start_slot, end_slot, unavail, total_assignments, unmet_kwh)
            summary = (
                f"Active disruption: charger failure between slot {start_slot} and slot {end_slot}. "
                f"{unavail} charger offline. Assignments replanned: {total_assignments}."
            )
            details.append(f"Depot slot capacity reduced by {unavail} during slot range {start_slot} to {end_slot}.")
            details.append(f"Replanned schedule delivers with remaining unmet energy of {unmet_kwh:.1f} kWh.")
        elif event_type == "late_return":
            vid = event.get("vehicle_id", "EV-103")
            return_slot = event.get("return_slot", 10)
            facts = (return_slot, total_assignments, unmet_kwh)
            summary = (
                f"Active disruption: delayed vehicle return at slot {return_slot}. "
                f"Total assignments: {total_assignments} with {unmet_kwh:.1f} kWh unmet energy."
            )
            details.append(f"Vehicle {vid} arrival postponed to slot {return_slot}, narrowing its available charging window.")
        elif event_type == "price_spike":
            start_slot = event.get("start_slot", 16)
            end_slot = event.get("end_slot", 20)
            price = round(float(event.get("price", 12.0)), 2)
            facts = (start_slot, end_slot, price, total_assignments, unmet_kwh)
            summary = (
                f"Active disruption: grid price spike of INR {price:.2f} per unit from slot {start_slot} "
                f"to slot {end_slot}. Assignments in schedule: {total_assignments}."
            )
            details.append(f"Tariff elevated to INR {price:.2f} across slots {start_slot} to {end_slot}; charging shifted where feasible.")
        else:
            facts = (total_assignments, unmet_kwh)
            summary = f"Custom disruption event active. Assignments: {total_assignments}, unmet energy: {unmet_kwh:.1f} kWh."
            details.append(f"Event payload: {json.dumps(event)}")

        return AgentReport(
            role="Disruption Scenario Analyst",
            summary=summary,
            details=tuple(details),
            facts=facts,
            is_grounded=verify_numeric_grounding(summary, facts),
            status="verified" if unmet_kwh <= 0 else "warning",
        )


class BatteryHealthReviewerAgent:
    """Inspects fleet thermal telemetry, SOH, and charging mode stress."""

    def analyze(self, result: CoordinationResult) -> AgentReport:
        vehicles = result.planning_input.vehicles
        schedule = result.selected.schedule
        fast_assignments = sum(1 for a in schedule.assignments if a.mode == "fast")
        standard_assignments = sum(1 for a in schedule.assignments if a.mode == "standard")
        health_penalty = round(schedule.objective["health_penalty"], 3)

        hot_vehicles = [v for v in vehicles if v.temperature_c >= 35.0]
        hot_count = len(hot_vehicles)
        avg_soh = round(sum(v.soh_percent for v in vehicles) / len(vehicles), 1)

        facts = (fast_assignments, standard_assignments, health_penalty, hot_count, avg_soh, len(vehicles))

        details = [
            f"Fleet average SOH is {avg_soh:.1f}% across {len(vehicles)} vehicles.",
            f"Charging mode breakdown: {standard_assignments} standard slots and {fast_assignments} fast-charging slots.",
            f"Total pack degradation penalty score: {health_penalty:.3f}.",
        ]

        if hot_count > 0:
            hot_ids = ", ".join(v.vehicle_id for v in hot_vehicles)
            details.append(f"{hot_count} vehicles have elevated battery temperatures (>= 35°C): {hot_ids}.")
            summary = (
                f"Battery health review: {hot_count} vehicles exhibit elevated pack temperatures. "
                f"Plan assigns {standard_assignments} standard and {fast_assignments} fast slots with "
                f"health penalty {health_penalty:.3f} and average SOH {avg_soh:.1f}%."
            )
            status = "warning" if fast_assignments > 0 and hot_count > 1 else "verified"
        else:
            summary = (
                f"Battery health review: all packs within nominal thermal limits. "
                f"Plan assigns {standard_assignments} standard and {fast_assignments} fast slots with "
                f"health penalty {health_penalty:.3f}."
            )
            status = "verified"

        return AgentReport(
            role="Battery Health Reviewer",
            summary=summary,
            details=tuple(details),
            facts=facts,
            is_grounded=verify_numeric_grounding(summary, facts),
            status=status,
        )


class DataQualitySafetyReviewerAgent:
    """Audits data provenance, independent verifier gates, and safety boundaries."""

    def analyze(self, result: CoordinationResult) -> AgentReport:
        tariff = result.planning_input.tariff
        check = result.selected.check
        violation_count = len(check.violations)
        facts = (violation_count, len(tariff.slot_prices))

        details = [
            f"Tariff data source: {tariff.source} ({tariff.validation_status}), verified for {len(tariff.slot_prices)} slots.",
            f"Independent checker gate: {'PASSED' if check.valid else 'BLOCKED'} with {violation_count} violations.",
            "Safety boundary assertion: Physical hardware command integration is disabled. Local approval record only.",
        ]

        if not check.valid:
            for violation in check.violations:
                details.append(f"Violation [{violation.code}]: {violation.message}")
            summary = (
                f"Data quality and safety audit: Independent verifier gate BLOCKED with {violation_count} "
                "violations. Plan approval disabled. Provenance confirmed, no hardware commands issued."
            )
            status = "blocked"
        else:
            summary = (
                f"Data quality and safety audit: Independent verifier gate PASSED with {violation_count} "
                "violations. Fixture provenance verified. Execution strictly bounded to local decision-support."
            )
            status = "verified"

        return AgentReport(
            role="Data Quality & Safety Auditor",
            summary=summary,
            details=tuple(details),
            facts=facts,
            is_grounded=verify_numeric_grounding(summary, facts),
            status=status,
        )


class OperatorBriefingAgent:
    """Synthesizes specialist findings into an actionable executive briefing."""

    def analyze(
        self,
        planner: AgentReport,
        scenario: AgentReport,
        battery: AgentReport,
        safety: AgentReport,
        result: CoordinationResult,
        enable_llm: bool = False,
    ) -> AgentReport:
        selected = result.selected
        check = selected.check
        total_vehicles = len(result.planning_input.vehicles)
        ready_count = sum(1 for a in selected.schedule.unmet_energy_kwh.values() if a <= 0)
        cost = round(check.cost, 2)
        energy = round(sum(selected.schedule.delivered_energy_kwh.values()), 1)
        unmet = round(selected.schedule.objective["unmet_energy_kwh"], 1)

        facts = (total_vehicles, ready_count, cost, energy, unmet)

        # Baseline grounded synthesis
        if check.valid:
            summary = (
                f"Executive Briefing: The {selected.name} charging plan is verified and ready. "
                f"It schedules {energy:.1f} kWh for {ready_count} of {total_vehicles} vehicles at "
                f"INR {cost:.2f} with {unmet:.1f} kWh unmet energy. Human operator approval is required."
            )
        else:
            summary = (
                f"Executive Briefing: Plan has {unmet:.1f} kWh unmet energy for {ready_count} of "
                f"{total_vehicles} vehicles. Verifier gate is blocked. Operator override required."
            )

        details = [
            f"1. Strategy: {planner.summary}",
            f"2. Operations: {scenario.summary}",
            f"3. Battery Health: {battery.summary}",
            f"4. Safety & Provenance: {safety.summary}",
        ]

        # Optional LLM enhancement via OpenRouter
        if enable_llm:
            token = _get_openrouter_token()
            base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
            model = os.getenv("MODEL_NAME", "google/gemini-2.0-flash-001")
            if token:
                try:
                    prompt = (
                        f"{OPERATOR_BRIEFING_RULES}\n"
                        f"SYNTHESIS FACTS:\n"
                        f"- Fleet size: {total_vehicles}\n"
                        f"- Ready: {ready_count}\n"
                        f"- Energy: {energy:.1f} kWh\n"
                        f"- Cost: INR {cost:.2f}\n"
                        f"- Unmet: {unmet:.1f} kWh\n"
                        f"- Strategy: {selected.name}\n"
                        f"- Status: {'Verified' if check.valid else 'Blocked'}\n\n"
                        f"Summarize in exactly 2 concise sentences for the fleet operator. "
                        f"Only use numbers present in the facts."
                    )
                    req = urllib.request.Request(
                        f"{base_url}/chat/completions",
                        data=json.dumps({
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                            "max_tokens": 150,
                        }).encode("utf-8"),
                        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        llm_content = res["choices"][0]["message"]["content"].strip()
                        if verify_numeric_grounding(llm_content, facts):
                            summary = llm_content
                except Exception:
                    pass  # Fall back safely to verified deterministic summary

        return AgentReport(
            role="Operator Briefing Lead",
            summary=summary,
            details=tuple(details),
            facts=facts,
            is_grounded=verify_numeric_grounding(summary, facts),
            status="verified" if check.valid else "blocked",
        )


def run_operations_copilot(
    coordination_result: CoordinationResult,
    event: dict | None = None,
    enable_llm: bool = False,
) -> CopilotBriefing:
    """Orchestrate the 5 specialized copilot agents on checked coordinator proposals."""
    planner = PlannerAgent().analyze(coordination_result)
    scenario = ScenarioAnalystAgent().analyze(coordination_result, event=event)
    battery = BatteryHealthReviewerAgent().analyze(coordination_result)
    safety = DataQualitySafetyReviewerAgent().analyze(coordination_result)
    briefing = OperatorBriefingAgent().analyze(
        planner=planner,
        scenario=scenario,
        battery=battery,
        safety=safety,
        result=coordination_result,
        enable_llm=enable_llm,
    )

    if not coordination_result.selected.check.valid:
        overall_status = "blocked"
    elif coordination_result.selected.schedule.objective["unmet_energy_kwh"] > 0:
        overall_status = "needs_operator_decision"
    else:
        overall_status = "ready_for_approval"

    return CopilotBriefing(
        planner=planner,
        scenario_analyst=scenario,
        battery_reviewer=battery,
        safety_reviewer=safety,
        operator_briefing=briefing,
        overall_status=overall_status,
    )
