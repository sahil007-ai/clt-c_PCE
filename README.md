# VoltAI — Verified EV Fleet Charging Planner

VoltAI is a local decision-support demonstration that produces an overnight,
30-minute-slot EV charging plan from versioned fleet, route, charger, and
tariff fixtures. It compares cost, readiness, and battery-health proposals;
checks the selected plan independently; handles simulated disruptions; and
requires explicit human approval before a local audit record is created.

It is not connected to chargers, vehicles, dispatch systems, or live customer
data. The included tariff and fleet data are clearly labelled fixtures.

## Current functions

- **Verified Streamlit dashboard**: `streamlit_app.py` displays checked plans,
  proposal trade-offs, fleet readiness, charging-load and tariff charts, data
  provenance, checker failures, and the local approval control.
- **Standalone visual dashboard**: `index.html` provides a non-operational
  design prototype with theme switching, simulated grid status, telematics
  filtering, Chart.js load and price visualisation, and strategy controls.
- **Deterministic scheduling**: `engine.scheduler.optimize_schedule` creates a
  30-minute-slot plan using parking windows, charger capacity, charging modes,
  tariff prices, departure energy targets, battery ceilings, and explicit
  unmet-energy slack.
- **Independent verification**: `engine.checker.check_schedule` recomputes
  energy needs, parking-window checks, charger capacity, duplicate assignments,
  mode limits, battery ceilings, and energy cost without importing the scheduler.
- **Proposal coordination**: `agent.graph.coordinate_plan` requests cost,
  availability, battery-health, and operator-weighted proposals through
  `agent.tools.EngineTools`, rejects invalid proposals when valid alternatives
  exist, and selects the proposal with the lowest weighted score.
- **Grounded operations copilot**: `agent.copilot.run_operations_copilot`
  produces planner, disruption, battery-health, data-quality/safety, and
  operator-briefing reports from checked results. Numeric claims are validated
  by `agent.grounding.verify_numeric_grounding`.
- **Disruption simulation**: `engine.events.apply_event` supports charger
  failures, late returns, tariff price spikes, and missing battery data.
  Missing battery data raises an error and blocks replanning instead of being
  guessed.
- **Validated cache refresh**: `live.routes` and `live.tariffs` validate
  refreshed payloads and retain the last valid cache when a refresh is rejected.
- **Local approval audit**: `agent.tools.record_approval` appends the approved
  schedule and operator name to `saved_outputs/approvals.jsonl`; it never sends
  commands to charging hardware.
- **Testing and evaluation**: the repository includes unit tests, a terminal
  demo, and a seeded scenario evaluator that reports checker validity,
  grounded explanations, infeasibility escalations, and baseline comparisons.

`index.html` remains an earlier standalone visual prototype. It is not used by
the scheduling engine and is retained only as a design demo.

## Architecture

```text
fixture or validated cache
          │
          ▼
  deterministic scheduler ──► independent checker
          │                         │
          └──────── tool boundary ──┘
                         │
                         ▼
                  coordinator proposals
                         │
                         ▼
         Streamlit dashboard + human approval record
```

The coordinator never calculates a plan itself; it only requests tool results
and selects a checked proposal. The dashboard never treats a failed check as a
valid plan.

## Setup and run

Python 3.11 is used in CI.

```bash
git clone https://github.com/sahil007-ai/clt-c_PCE.git
cd clt-c_PCE
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

To run the standalone HTML prototype, serve the repository directory and open
the printed URL:

```bash
python -m http.server 8000
```

The Streamlit dashboard is available at `http://localhost:8501` and the HTML
prototype at `http://localhost:8000`.

## Visual preview

The standalone dashboard includes the following visual views and controls:

| Dashboard overview | Dark theme |
| --- | --- |
| ![VoltAI dashboard light theme](docs/tutorial/images/09_full_dashboard_light.png) | ![VoltAI dashboard dark theme](docs/tutorial/images/10_full_dashboard_dark.png) |

| AI action center | Streamlit engine view |
| --- | --- |
| ![VoltAI AI action center](docs/tutorial/images/04_ai_action_center.png) | ![VoltAI Streamlit engine tab](docs/tutorial/images/12_view_switcher_streamlit_tab.png) |

More captured states, including telematics filters, grid status, charts, and
theme-specific views, are available in [`docs/tutorial/images`](docs/tutorial/images).

Run the terminal demo, test suite, and reproducible evaluation with:

```bash
python -m scripts.demo
pytest
python -m evaluation.run --seed 42 --scenarios 50
```

The evaluation writes local results to `evaluation/results/`; generated results
and local approval records are intentionally ignored by Git.

## Main Python functions

| Function | Purpose |
| --- | --- |
| `engine.generate.load_planning_input` | Loads typed fleet, route, charger, and cache-first tariff data. |
| `engine.energy.calculate_all_energy_needs` | Calculates each vehicle's required and maximum charge. |
| `engine.scheduler.optimize_schedule` | Builds a deterministic charging schedule from objective weights. |
| `engine.checker.check_schedule` | Independently validates assignments and calculates verified cost. |
| `engine.events.apply_event` | Creates an adjusted planning snapshot for a supported disruption. |
| `agent.graph.coordinate_plan` | Generates, checks, scores, and selects proposals. |
| `agent.copilot.run_operations_copilot` | Creates grounded specialist reports and an operator briefing. |
| `agent.tools.record_approval` | Writes a local approval record without hardware execution. |
| `evaluation.run.run_evaluation` | Runs reproducible scenario evaluation and baseline comparison. |

## Data and safety

Read [data provenance and tariff-source findings](docs/DATA_SOURCES.md) before
changing fixture values or adding a refresh adapter. Read the
[safety review](docs/SAFETY.md) before considering any external integration.

The optional variables in `.env.example` are reserved for a future approved
source adapter. Leaving them unset keeps the project in safe cache-first mode.

## Repository layout

```text
streamlit_app.py       Canonical Streamlit dashboard
index.html             Standalone non-operational visual prototype
data/                  Versioned fixtures and explicitly labelled cache
engine/                Schemas, energy calculations, scheduler, checker, events
agent/                 Tool boundary, coordinator, copilot, numeric grounding
live/                  Cache and refresh validation helpers
evaluation/            Baselines and seeded evaluation runner
tests/                 Engine, checker, data, and coordinator tests
scripts/demo.py        Normal and disruption-flow walkthrough
docs/                  Demo, data-provenance, and safety documentation
```

## Technology

| Area | Implementation |
| --- | --- |
| Runtime | Python 3.11+ |
| Dashboard | Streamlit, pandas, Altair |
| Scheduling and verification | Python standard library, typed dataclasses |
| Agent orchestration | Deterministic coordinator and specialist report classes |
| Observability & Tracing | LangSmith `@traceable` span tracing |
| Optional language model | OpenRouter briefing enhancement with numeric grounding guard |
| Data | Versioned JSON fixtures and cache files |
| Testing | unittest-compatible tests run with pytest |
| Automation | GitHub Actions |

## LangSmith Observability & Tracing

VoltAI is instrumented with [LangSmith](https://smith.langchain.com) for observability across the multi-agent copilot, proposal generation, tool execution, and benchmark evaluations:

- **Automatic Environment Sync**: `agent/tracing.py` reads `.env` automatically and synchronizes the supported `LANGSMITH_*` and `LANGCHAIN_*` tracing variables when credentials are present.
- **Span Hierarchy**:
  - `VoltAI_OperationsCopilot` (top-level workflow chain)
    - `PlannerAgent` (fleet schedule analysis)
    - `ScenarioAnalystAgent` (disruption response & sensitivity)
    - `BatteryHealthReviewerAgent` (degradation & depth-of-discharge checks)
    - `DataQualitySafetyReviewerAgent` (telematics confidence & constraint compliance)
    - `OperatorBriefingAgent` (grounded briefings & OpenRouter Nemotron LLM enhancement)
  - `VoltAI_CoordinatorPlan` (candidate schedule generation, scoring, and selection)
  - `VoltAI_SeededEvaluation` (50-scenario reproducible test runner)
  - Tool spans: `verify_numeric_grounding`, `EngineTools.propose`, `EngineTools.record_approval`
- **Graceful Fallback**: If the LangSmith package or credentials are unavailable, the `@traceable` wrapper falls back to the original function and the application continues offline.

## Boundaries and next production work

The scheduler is deterministic and fixture-backed; it is not a physical
charger-control or billing system. A production deployment would require
approved live-data adapters, real telematics, physical charger integration,
authentication and authorization, durable audit storage, monitoring, and a
formal optimization solver validated against operational requirements.

For the implementation history and completed checklist, see
[PROJECT_STATUS.md](PROJECT_STATUS.md). A walkthrough is available in
[docs/DEMO.md](docs/DEMO.md).
