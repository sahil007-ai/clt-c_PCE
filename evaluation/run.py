"""Seeded, reproducible scenario evaluation runner."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from agent.graph import coordinate_plan
from engine.generate import DEFAULT_DATA_DIR, PROJECT_ROOT, load_planning_input
from engine.schemas import ObjectiveWeights
from evaluation.baselines import baseline_results


def _event_for(index: int, rng: random.Random) -> dict | None:
    event_type = index % 4
    if event_type == 0:
        return None
    if event_type == 1:
        return {"type": "charger_failure", "start_slot": 12, "end_slot": 18, "unavailable_chargers": 1}
    if event_type == 2:
        return {"type": "late_return", "vehicle_id": "EV-103", "return_slot": 8 + rng.randint(0, 3)}
    return {"type": "price_spike", "start_slot": 16, "end_slot": 20, "price": 12.0}


def run_evaluation(seed: int = 42, scenarios: int = 50) -> dict:
    rng = random.Random(seed)
    planning_input = load_planning_input(DEFAULT_DATA_DIR)
    valid_count = 0
    grounded_count = 0
    infeasible_count = 0
    total_cost = 0.0
    for index in range(scenarios):
        result = coordinate_plan(
            planning_input,
            ObjectiveWeights(cost=60, availability=30, health=10),
            event=_event_for(index, rng),
        )
        valid_count += int(result.selected.check.valid)
        grounded_count += int(result.explanation_is_grounded)
        infeasible_count += int(not result.selected.check.valid)
        total_cost += result.selected.check.cost
    baselines = baseline_results(planning_input)
    return {
        "seed": seed,
        "scenarios": scenarios,
        "schedules_passing_checker": valid_count,
        "grounded_explanations": grounded_count,
        "infeasible_escalations": infeasible_count,
        "average_selected_cost": round(total_cost / scenarios, 2),
        **baselines,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenarios", type=int, default=50)
    args = parser.parse_args()
    results = run_evaluation(args.seed, args.scenarios)
    output_dir = PROJECT_ROOT / "evaluation" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"evaluation-{args.seed}-{args.scenarios}.json"
    output.write_text(
        json.dumps({"generated_at": datetime.now(UTC).isoformat(), **results}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(results, indent=2))
    print(f"Saved results to {output}")


if __name__ == "__main__":
    main()
