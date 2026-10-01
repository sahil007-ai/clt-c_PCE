# EV Fleet Charging Agent — Project Plan and Dashboard Prototype

This repository currently contains VoltAI dashboard prototypes for an electric-vehicle fleet. The constraint-based optimizer, independent schedule verifier, live tariff and route data, and coordinating agent described below are the target system; they have not yet been implemented in this repository.

Built for TECHNOVA '26, Track 2 (AI Agent Challenges), 1 October 2026, Nagpur.

> **Current implementation:** a Streamlit prototype (`app.py`) and a standalone interactive web prototype (`index.html`) with hard-coded demonstration data. For an audited list of built features, README corrections, and the completion plan, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

---

## Why this is not a chatbot wrapped around a scheduler

| Property | How it is achieved |
| --- | --- |
| Correct numbers | The language model never does arithmetic. Schedules come from an optimizer; costs and constraints come from plain tested functions. |
| Verifiable output | An independent checker recomputes every constraint from raw data. A schedule that fails the checker is never presented as valid. |
| Honest live data | Tariffs and routes carry source, fetch time, and validation status. Failed or implausible fetches fall back to cached data and say so. |
| Real decisions | The agent chooses tools, resolves objective conflicts, handles infeasibility, and replans. It does not follow a fixed script. |
| Human control | Nothing executes without explicit approval. Infeasible cases are escalated with options, never silently resolved. |
| Measured quality | A reproducible evaluation harness reports validity, optimality gap, and agent decision quality. |

---

## Results

> Fill in after running the evaluation (see [Evaluation](#evaluation)). Leave blank rather than estimate.

| Metric | Result |
| --- | --- |
| Schedules passing the checker (random scenario suite) | [X of N] |
| Cost reduction versus charge-immediately baseline | [X%] |
| Cost gap versus greedy baseline | [X%] |
| Vehicles ready with margin, normal night | [X of 12] |
| Infeasible scenarios correctly escalated | [X of N] |
| Explanations whose numbers all trace to tool output | [X%] |

---

## Architecture

```
                  Operator request / disruption event
                                  |
                                  v
  +-------------------------------------------------------------+
  |  Agent layer (LangGraph)                                    |
  |  Coordinator <-> Cost agent / Availability agent /          |
  |                  Battery agent                              |
  +-------------------------------+-----------------------------+
                                  | tool calls
                                  v
  +-------------------------------------------------------------+
  |  Deterministic engine (no language model)                   |
  |  energy needs -> optimizer -> checker -> event simulator    |
  +-------------------------------+-----------------------------+
                                  | reads
                                  v
  +-------------------------------------------------------------+
  |  Data layer                                                 |
  |  cached files (always)   <--refresh--   live sources        |
  |  fleet, routes, tariffs                 tariff search,      |
  |                                         routing service     |
  +-------------------------------------------------------------+
                                  |
                                  v
                Streamlit dashboard + human approval
```

The engine never calls the network. Live data only refreshes the cache, so a schedule is always computed from a fixed, inspectable snapshot.

### Agents

| Agent | Goal | Tools |
| --- | --- | --- |
| Cost agent | Cheapest valid schedule | Optimizer (cost-heavy weights), checker |
| Availability agent | Every vehicle ready with margin | Optimizer (readiness-heavy weights), checker |
| Battery agent | Least battery wear | Optimizer (health-heavy weights), checker |
| Coordinator | Collect proposals and objections, resolve conflicts, state what the chosen plan gives up, handle disruptions, request approval | All of the above, event simulator, data refresh |

Each specialist critiques the others' proposals using checker output. The coordinator's explanation must cite tool results.

> **Current status:** no LangGraph agent, specialist agents, or agent tools are implemented yet. The current dashboard recommendation text is a local demonstration rule, not an LLM or optimizer result.

---

## Optimization model

Slots are 30 minutes over a 24-hour window. Chargers are treated as interchangeable.

```
Decision variables
  x[v,t,m] in {0,1}   vehicle v charges in slot t in mode m (standard or fast)
  s[v]     >= 0       unmet energy for vehicle v (slack)

Constraints
  1. Parked only:     x[v,t,m] = 0 outside [return_v, departure_v)
  2. Charger limit:   sum over v,m of x[v,t,m] <= chargers_available(t)
  3. One mode:        sum over m of x[v,t,m] <= 1
  4. Energy:          sum over t,m of power_m * dt * efficiency * x[v,t,m] + s[v]
                        >= required_kWh_v + safety_reserve_v
  5. Battery ceiling: state of charge never exceeds the configured ceiling

Objective (weights set per agent)
  minimize  w_cost  * sum of price_t * power_m * dt * x[v,t,m]
          + w_avail * sum of s[v]
          + w_health * sum of health_penalty(m, state_of_charge_band)
```

Slack makes infeasibility explicit: a positive `s[v]` is reported to the agent as a named, quantified shortfall instead of a solver failure. A greedy scheduler (sort by departure, fill cheapest free slots) is kept as a fallback and as an evaluation baseline.

---

## Live data

| Data | Primary source | Refresh method | Validation |
| --- | --- | --- | --- |
| Electricity tariff (time-of-day) | Entered manually from the Maharashtra Electricity Regulatory Commission multi-year tariff order for the Maharashtra State Electricity Distribution Company Limited (Case No. 217 of 2024, 28 March 2025) and its review order (Case No. 75 of 2025, 25 June 2025). Categories: LT VIII and HT IX (electric vehicle charging stations). Page references are recorded with the data. | Optional: Tavily search restricted to merc.gov.in and mahadiscom.in; a language model extracts a structured table | The extracted table must match the manual table or be flagged. Prices within a plausible range, all 24 hours covered, no overlapping windows. No assumption is made about which hours are cheap. |
| Route distances and durations | Open Route Service matrix (free standard plan: 500 matrix requests per day, 40 per minute; key from account.heigit.org) | One matrix call between the depot and 6 to 8 stops | Distances positive and plausible against straight-line distance. On failure, use the cache. |

Rules that apply to all live data:

- **Official source first.** The tariff is entered from the regulator's order and cited. Search is a refresh and a cross-check, not the source, because search results for this topic mix other states, other countries, and consumer blogs, and a misread digit would pass the checker unnoticed.
- **Cache first.** Data is saved to `data/cache/`. The engine reads only the cache.
- **Provenance everywhere.** Every record carries source, fetch time, and a status of `verified-by-rule`, `extracted-unverified`, or `cached`. The dashboard shows it.
- **No gap filling by the model.** If extraction fails, the system says so and uses the cache.
- **Refresh is explicit.** It is a button and a command, never part of a scheduling run.
- **Tariff caveat.** Retail electricity in India is set by state tariff orders with time-of-day rates, not minute-by-minute market prices. "Live" means the currently published tariff, not a spot price.
- **Night rebate.** The June 2025 review order removed the night time-of-day rebate (midnight to 6 AM) for the distribution company's tariff. [Confirm whether this applies to the electric vehicle categories and record the slabs used.] If overnight prices are flat, the cost trade-off comes from the scenarios (daytime idle windows, price spikes), not from a cheap-night assumption.

---

## Verification and trust

- **Independent checker.** `engine/checker.py` recomputes parked windows, charger limits, delivered energy, and the battery ceiling from raw inputs. It shares no code path with the optimizer.
- **Numeric grounding.** Every number in an agent explanation is matched against tool output. Unmatched numbers are flagged. [Built / Planned]
- **Adversarial tests.** The checker is tested against deliberately corrupted schedules and must catch each one.
- **Human approval.** The approve action is the only way a plan becomes final. The agent can propose, never commit.

---

## Scenarios

1. **Normal night.** Three candidate schedules with a cost, readiness, and battery-wear comparison and a recommendation that states its trade-off.
2. **Infeasible night.** Too much energy needed in too little time. The agent names which vehicles cannot be satisfied and why, and offers options: swap routes, allow fast charging at a battery-health cost, delay a departure. It asks for approval.
3. **Charger failure.** A charger goes offline mid-night. Only affected vehicles are replanned, and the diff is shown.
4. **Late return.** A vehicle returns after its planned window. Dependent charging is reshuffled.
5. **Price spike.** A tariff window changes. The agent re-evaluates only the affected slots.
6. **Missing data.** A vehicle has no battery reading. The agent flags the assumption instead of guessing.
7. **Live data failure.** The tariff lookup returns garbage. The system rejects it, uses the cache, and says so.

---

## Evaluation

```bash
python -m evaluation.run --seed 42 --scenarios 50
```

| Layer | What is measured |
| --- | --- |
| Engine | Checker pass rate, constraint violations found, solve time |
| Optimality | Cost versus charge-immediately baseline and greedy baseline |
| Agent decisions | Correct escalation on infeasible cases, correct replanning on disruptions |
| Explanations | Share of numbers traceable to tool output |
| Data layer | Rejection rate of corrupted tariff and route fixtures |

The seeded generator makes every result reproducible. Results are written to `evaluation/results/`.

---

## Failure boundaries

- It will not present a schedule that fails the checker.
- It will not trade away availability for cost without saying so and asking.
- It will not guess missing sensor data or fill gaps in live data.
- It does not execute anything. Every plan needs human approval.
- If the language model is unavailable, the engine still produces and verifies schedules, and the dashboard shows saved agent runs.
- If live sources fail, it falls back to cached data and labels it.

---

## Tech stack

| Layer | Tools |
| --- | --- |
| Language | Python 3.11 |
| Data | JSON and CSV files, pandas (no database) |
| Optimization | PuLP with the CBC solver |
| Agent orchestration | LangGraph |
| Language model | [model name], one key, tool calling |
| Live data | Tavily (optional tariff refresh), Open Route Service (route matrix) |
| Dashboard | Streamlit, Plotly |
| Testing | pytest |

## Repository structure

```
ev_fleet/
  data/
    cache/             tariffs.json, routes.json (with provenance fields)
    fleet.json
  engine/              generate.py, energy.py, scheduler.py, checker.py, events.py
  live/                tariffs.py, routes.py, cache.py
  agent/               tools.py, graph.py, prompts.py, grounding.py
  evaluation/          run.py, baselines.py, fixtures/, results/
  tests/               test_engine.py, test_checker.py, test_live_validation.py
  saved_outputs/       recorded agent runs (demo fallback)
  app.py               Streamlit dashboard
  .env.example
  requirements.txt
  README.md
```

---

## Run the current prototypes

The Streamlit prototype requires Python packages used by `app.py` (`streamlit`, `pandas`, `numpy`, and `altair`). A dependency manifest has not been added yet.

```bash
streamlit run app.py
```

Open `index.html` in a modern browser to run the standalone prototype. It loads Chart.js and Google Fonts from CDNs.

## Planned full-system setup

```bash
git clone [repository link]
cd ev_fleet
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # then add your keys
```

`.env` variables:

```
MODEL_API_KEY=
TAVILY_API_KEY=
OPENROUTESERVICE_API_KEY=         # free key from account.heigit.org
```

## Planned full-system commands

```bash
python -m engine.generate                 # synthetic fleet, seeded
python -m live.refresh                    # fetch tariffs and routes into the cache
streamlit run app.py                      # dashboard
streamlit run app.py -- --offline         # cached data only, no network
pytest                                    # unit tests
python -m evaluation.run --seed 42 --scenarios 50
```

---

## Design decisions

| Decision | Reason |
| --- | --- |
| Optimizer and checker are plain Python, not the language model | Language models make arithmetic errors; judges and operators can verify every number. |
| Checker is independent of the optimizer | A bug in one cannot hide a bug in the other. |
| Tariff entered from the official order; search is a refresh, not the source | Search results mix other states, countries, and consumer blogs; a misread digit would pass the checker. |
| Cache first, live as refresh | The demo and the schedule never depend on a network call succeeding. |
| Slack variables instead of hard failure | Infeasibility becomes a quantified, explainable result the agent can act on. |
| No database | The data is small and regenerated; a database would add setup cost with no benefit. |
| Streamlit, no separate backend | The dashboard imports the engine directly, which keeps the build small and the code easy to explain. |

## Data, assumptions, and provenance

| Item | Value | Source | Status |
| --- | --- | --- | --- |
| Vehicle model | Tata Ace EV, 21.3 kWh lithium iron phosphate battery, certified range 154 km (161 km on the Ace EV 1000 variant) | Trade and news sites. [Replace with the Tata Motors specification page.] | Secondary source |
| Charging times | Regular charge 6 to 7 hours (20% to 100%); fast charge 105 minutes (10% to 80%) | Same as above | Secondary source |
| Energy consumption | About 0.14 kWh per km at the certified range; about 0.17 at a 125 km practical range | Computed in the spreadsheet `Vehicle inputs` sheet | Derived |
| Charging power | Regular: about 2.4 to 2.8 kW average; fast: about 8.5 kW average. Losses ignored. | Computed from the charging times | Derived |
| Tariff | See [Live data](#live-data) | Regulator order, with page references | [Primary, confirm after reading the order] |
| Distances | Open Route Service matrix | openrouteservice.org | Live with cache |
| Fleet, return and departure times, charger count | One depot, 12 vehicles, 4 chargers, 24-hour window in 30-minute slots | Synthetic, generated with a fixed seed | Assumed |

No real customers, personal data, or private systems are involved. No partnership with any manufacturer or distribution company is implied.

## Limitations

- Single depot, fixed slots, interchangeable chargers.
- The tariff is a published schedule, not a market price. It is entered from the regulator's order; the optional search refresh carries extraction risk (mitigated by validation and provenance labels).
- The electricity tariff structure for the electric vehicle categories, including whether any night rebate applies, must be confirmed from the order. Overnight prices may be nearly flat.
- Battery wear uses penalty terms, not a physical degradation model.
- Vehicle-to-route assignment is an input, not optimized.
- Energy consumption per kilometre is a constant, not a function of load, speed, or temperature.

## Roadmap toward production

- Multi-depot and vehicle-to-route co-optimization.
- Rolling-horizon replanning with live telematics instead of scripted events.
- Uncertainty in return times and energy use (stochastic or robust optimization).
- Physics-informed battery degradation model.
- Persistence, audit log of approvals, and authentication for operators.
- Tracing and monitoring of agent runs and live-data failures.

---

## AI use

AI tools were used during development, as the event rules permit. The team can explain the architecture, the optimization model, the checker, the prompts, the live-data validation, and the failure boundaries.

## Team

| Name | Role |
| --- | --- |
| [Name] | Engine, optimization, checker, evaluation |
| [Name] | Agent layer, live data, dashboard |

## Event

TECHNOVA '26, 1 October 2026, Track 2: AI Agent Challenges.
