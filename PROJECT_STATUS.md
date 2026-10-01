# Project Status: VoltAI EV Fleet Optimization

Last reviewed: 1 October 2026

## What is built

The repository currently delivers two front-end dashboard prototypes and a Streamlit theme configuration.

| Area | Current implementation |
| --- | --- |
| Streamlit dashboard | `app.py` renders an EV-fleet dashboard with KPI cards, an eight-vehicle telematics table, a minimum-SOC filter, three objective-weight sliders, a dual-axis Altair chart, dynamic recommendation text, and a visual schedule-acceptance confirmation. |
| Standalone web dashboard | `index.html` renders a responsive VoltAI dashboard using Chart.js. It includes a static eight-vehicle data set, search and health-status filters, cost/longevity sliders that total 100%, strategy presets, a grid-connected/disconnected toggle, a dual-axis price/load chart with V2G-negative load values, dynamic recommendation text, and a visual acceptance state. |
| Visual design | Both dashboards use a dark VoltAI theme. `.streamlit/config.toml` defines the Streamlit colour palette. |
| Prototype logic | Dashboard controls update local, hard-coded data and UI state in the browser or Streamlit session. The Python file passes a syntax check. |

## What is not built yet

The README describes the intended full product, but its optimizer, validation, data, agent, and evaluation layers do not exist in this repository yet. In particular, there is no:

- fleet, tariff, route, or cached-data directory;
- charging optimizer, greedy baseline, schedule checker, event simulator, or battery model;
- LangGraph workflow, LLM integration, tool layer, numeric grounding, or human-approval audit trail;
- live tariff or route integration, provenance validation, or fallback cache;
- dependency manifest, automated test suite, evaluation runner, or saved demo outputs;
- backend or charger-controller integration. The current “accept/apply” buttons only change the UI and must not be treated as operational control.

The dashboard values, pricing, schedules, savings, fleet KPIs, V2G amounts, and AI recommendations are demonstration data. They are not calculated from live inputs or an optimization result.

## README review and changes noted

The previous README was a target architecture/specification rather than an accurate record of the checked-in implementation. It has now been clarified to:

- identify the repository as a prototype dashboard plus planned system;
- link to this status document;
- state that no LangGraph agent is currently implemented;
- provide commands for the two available prototypes; and
- label the architecture, setup, and run commands for the future full system as planned.

The following README claims remain future work, not current capabilities: the constraint optimizer, independent checker, live data cache, multiple agents, evaluations/results, PyTest coverage, and all referenced directories and commands. The planned dependencies and integrations should only be documented as installed once their files and configuration are added.

## Completion task list

### 1. Establish a runnable project foundation

- [ ] Choose one canonical interface: Streamlit or the standalone web dashboard; document whether the other is kept as a design demo.
- [ ] Add `requirements.txt` (and, if needed, a lock file) for the selected Python implementation.
- [ ] Add `.env.example`, a clear install guide, and configuration validation.
- [ ] Replace hard-coded demo data with versioned fixture files for fleet, tariffs, routes, and chargers.
- [ ] Add a test framework and CI workflow that run on every change.

### 2. Build the deterministic scheduling engine

- [ ] Define the fleet, charger, tariff, route, and schedule schemas.
- [ ] Calculate vehicle energy requirements from SOC, battery capacity, reserve, and planned route distance.
- [ ] Implement the 30-minute-slot charging optimizer, including charger capacity, parking windows, charging modes, energy targets, and battery ceilings.
- [ ] Include explicit unmet-energy slack and return named, quantified infeasibility results.
- [ ] Implement a separate schedule checker that recomputes every constraint without sharing optimizer logic.
- [ ] Add a greedy/charge-immediately baseline for comparison.

### 3. Connect the engine to an honest dashboard

- [ ] Load schedules, costs, readiness, and battery-health trade-offs from engine output instead of constants.
- [ ] Make slider values objective weights passed to the optimizer.
- [ ] Render per-vehicle charging slots, delivered energy, cost, violations, and a checker result.
- [ ] Replace the simulated acceptance control with an explicit approval record; keep any real charger integration disabled until authorized and secured.
- [ ] Clearly label fixture, cached, stale, and live data in the UI.

### 4. Add agent and disruption capabilities

- [ ] Implement the tool boundary between an agent and deterministic engine; the agent must never calculate schedule values itself.
- [ ] Add the coordinator and, if still useful, cost, availability, and battery specialist roles.
- [ ] Ground every number in generated explanations in tool output.
- [ ] Implement charger-failure, late-return, price-spike, missing-data, and infeasible-night scenarios with targeted replanning.
- [ ] Keep a human approval step before finalizing or sending any schedule onward.

### 5. Add validated data and measurement

- [ ] Create cache files with source, fetch time, and validation-status fields.
- [ ] Implement tariff and route refreshers with validation and a cache-only fallback.
- [ ] Confirm the tariff categories, slabs, and night-rebate treatment against primary sources before using them in calculations.
- [ ] Add adversarial checker tests and fixture-based live-data validation tests.
- [ ] Build the seeded evaluation runner and publish measured results in the README only after it runs.

### 6. Finish for demonstration and handoff

- [ ] Replace placeholder repository URL, model name, and team entries in the README.
- [ ] Reconcile the README’s stated tech stack with the dependencies actually used (the current Streamlit prototype uses Altair, not Plotly).
- [ ] Add screenshots or a short demo script for normal, infeasible, and disruption scenarios.
- [ ] Perform a final safety review so prototype buttons cannot be mistaken for real operational actions.

## Verification performed

- Repository files and Git history were reviewed.
- `python -m py_compile app.py` completed successfully.
- No functional tests were available to run.
