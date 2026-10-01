# VoltAI — Verified EV Fleet Charging Planner

VoltAI is a local decision-support demonstration that produces an overnight,
30-minute-slot EV charging plan from versioned fleet, route, charger, and
tariff fixtures. It compares cost, readiness, and battery-health proposals;
checks the selected plan independently; handles simulated disruptions; and
requires explicit human approval before a local audit record is created.

It is not connected to chargers, vehicles, dispatch systems, or live customer
data. The included tariff and fleet data are clearly labelled fixtures.

## What is implemented

- Streamlit is the canonical interface: it displays verified plans, candidate
  trade-offs, per-vehicle readiness, price/load charts, data provenance, and
  checker failures.
- A deterministic slot scheduler considers parking windows, per-slot charger
  capacity, charging modes, departure energy targets, maximum SOC, and explicit
  unmet-energy slack.
- An independent checker recomputes all schedule constraints and cost without
  importing the scheduler.
- A tool-mediated deterministic coordinator evaluates cost, availability,
  battery-health, and operator-weighted proposals. Numeric explanations are
  checked against tool facts.
- Charger-failure, late-return, price-spike, and missing-battery-data scenarios
  are represented as explicit events. Missing data blocks a plan rather than
  being guessed.
- Tariff and route cache refresh helpers validate provenance and reject bad data
  in favour of the last valid cache.
- Unit tests, a GitHub Actions workflow, a terminal demo, and a seeded
  evaluation runner are included.

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
streamlit run app.py
```

Run the terminal demo, test suite, and reproducible evaluation with:

```bash
python -m scripts.demo
pytest
python -m evaluation.run --seed 42 --scenarios 50
```

The evaluation writes local results to `evaluation/results/`; generated results
and local approval records are intentionally ignored by Git.

## Data and safety

Read [data provenance and tariff-source findings](docs/DATA_SOURCES.md) before
changing fixture values or adding a refresh adapter. Read the
[safety review](docs/SAFETY.md) before considering any external integration.

The optional variables in `.env.example` are reserved for a future approved
source adapter. Leaving them unset keeps the project in safe cache-first mode.

## Repository layout

```text
app.py                 Canonical Streamlit dashboard
data/                  Versioned fixtures and explicitly labelled cache
engine/                Schemas, energy calculations, scheduler, checker, events
agent/                 Tool boundary, coordinator, numeric grounding
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
| Agent orchestration | LangGraph StateGraph (Coordinator & Multi-Agent Copilot) |
| Language model | OpenRouter (`nvidia/nemotron-3-ultra-550b-a55b:free`) with numeric grounding guard |
| Data | Versioned JSON fixtures and cache files |
| Testing | unittest-compatible tests run with pytest |
| Automation | GitHub Actions |

## Boundaries and next production work

The scheduler is deterministic and fixture-backed; it is not a physical
charger-control or billing system. A production deployment would require
approved live-data adapters, real telematics, physical charger integration,
authentication and authorization, durable audit storage, monitoring, and a
formal optimization solver validated against operational requirements.

For the implementation history and completed checklist, see
[PROJECT_STATUS.md](PROJECT_STATUS.md). A walkthrough is available in
[docs/DEMO.md](docs/DEMO.md).
