# Project Status: VoltAI EV Fleet Charging Planner

Last updated: 1 October 2026

## Delivered system

VoltAI is now a runnable, fixture-backed EV fleet charging demonstration. The
canonical application is `app.py`, a Streamlit dashboard whose plans and
recommendations are calculated by the deterministic engine and independently
verified before display. `index.html` is retained only as a clearly labelled,
non-operational visual design prototype.

The system is intentionally decision support only. It has no charger, vehicle,
dispatch, or live customer-data integration.

## Completion checklist

### 1. Project foundation

- [x] Selected Streamlit as the canonical interface and documented `index.html` as a design demo.
- [x] Added `requirements.txt` and Python 3.11 GitHub Actions test workflow.
- [x] Added `.env.example`, installation/run documentation, and cache-first configuration behaviour.
- [x] Replaced application hard-coding with versioned fleet, route, charger, tariff, and cache fixtures.
- [x] Added unittest-compatible tests run through pytest.

### 2. Deterministic planning and verification

- [x] Defined typed fleet, route, charger, tariff, assignment, schedule, and check-result schemas.
- [x] Implemented departure energy needs from SOC, battery capacity, route demand, reserve, target SOC, and maximum SOC.
- [x] Implemented a deterministic, feasible-first 30-minute slot scheduler with parking windows, capacity, modes, objective weights, and throttled final slots.
- [x] Represented infeasibility as per-vehicle unmet-energy slack.
- [x] Implemented an independent checker for windows, capacity, one-mode-per-slot, energy limits, battery ceiling, and cost.
- [x] Added charge-immediately and cheap-slot baseline schedules.

### 3. Verified dashboard

- [x] Rendered checked schedule cost, energy, readiness, proposal trade-offs, chart, and per-vehicle values from engine output.
- [x] Connected dashboard priorities to coordinator objective weights.
- [x] Displayed schedule verification failures and disabled approval for blocked plans.
- [x] Replaced simulated execution with an explicit local approval record that never sends hardware commands.
- [x] Displayed fixture/cache data provenance in the dashboard.

### 4. Coordinator and scenarios

- [x] Added a tool boundary so coordinator logic cannot calculate schedules directly.
- [x] Added cost, availability, battery-health, and operator-weighted proposal roles with a coordinator selection step.
- [x] Added a numeric-grounding guard for coordinator explanations.
- [x] Added charger failure, late return, price spike, and missing-battery-data scenarios; missing data blocks the run.
- [x] Kept explicit human approval as the only finalization action.
- [ ] Add an optional grounded multi-agent operations copilot: planner, scenario analyst, battery-health reviewer, data-quality and safety reviewer, and operator briefing agent. Agents may interpret requests, compare verified proposals, and explain trade-offs, but may not calculate schedules, invent data, bypass the checker, or send hardware commands.

### 5. Data validation and measurement

- [x] Added cache payload provenance requirements (`source`, `fetched_at`, and `validation_status`).
- [x] Added tariff and route validation plus explicit cache-fallback refresh helpers.
- [x] Reviewed the cited MERC proceedings and documented why the original 2025 order must not be copied into the demo fixture without a current primary-source review. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
- [x] Added corrupted-input and independent-checker tests.
- [x] Added a seeded evaluation runner. The latest local 50-scenario run produced 38 verified schedules, 12 explicit infeasibility escalations, and 50 grounded explanations.

### 6. Demonstration and handoff

- [x] Replaced README placeholders with the repository URL and the actual implementation/technology description.
- [x] Reconciled the tech stack with code: Streamlit, pandas, Altair, standard-library scheduling, pytest, and GitHub Actions.
- [x] Added a terminal demo script covering normal planning and charger failure.
- [x] Completed a safety review and made the HTML design prototype explicitly non-operational.

## Verification performed

- `pytest -q`: 11 passed.
- Python compilation completed for the application, engine, agent, live-data, evaluation, demo, and test modules.
- `python -m evaluation.run --seed 42 --scenarios 50` completed successfully.
- Streamlit started successfully on a local-only `127.0.0.1` test server.

## Production boundaries

Before use outside a demonstration, add an approved live-data adapter and
current tariff review, real telematics, a formal optimizer validated for
operational requirements, authentication/authorization, durable audit storage,
monitoring, and a separately reviewed hardware command integration. The
existing checker should remain a blocking gate.
