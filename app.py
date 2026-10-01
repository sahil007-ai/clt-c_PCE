"""VoltAI Streamlit dashboard backed exclusively by verified engine output."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from agent.graph import coordinate_plan
from agent.tools import record_approval
from engine.energy import calculate_all_energy_needs
from engine.generate import PROJECT_ROOT, load_planning_input
from engine.schemas import ObjectiveWeights


st.set_page_config(
    page_title="VoltAI — Verified EV Fleet Planning",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


EVENTS: dict[str, dict | None] = {
    "Normal planning run": None,
    "Charger failure (slots 12–17)": {
        "type": "charger_failure",
        "start_slot": 12,
        "end_slot": 18,
        "unavailable_chargers": 1,
    },
    "Late return (EV-103)": {"type": "late_return", "vehicle_id": "EV-103", "return_slot": 10},
    "Price spike (slots 16–19)": {"type": "price_spike", "start_slot": 16, "end_slot": 20, "price": 12.0},
    "Missing battery reading": {"type": "missing_battery_data"},
}


def slot_label(slot: int, slot_minutes: int = 30) -> str:
    minutes = slot * slot_minutes
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def schedule_chart_data(planning_input, schedule) -> pd.DataFrame:
    load_by_slot = {slot: 0.0 for slot in range(planning_input.chargers.horizon_slots)}
    for assignment in schedule.assignments:
        load_by_slot[assignment.slot] += assignment.energy_kwh / (
            planning_input.chargers.slot_minutes / 60
        )
    return pd.DataFrame(
        {
            "Time": [slot_label(slot, planning_input.chargers.slot_minutes) for slot in load_by_slot],
            "Charging load (kW)": list(load_by_slot.values()),
            "Tariff (INR/kWh)": list(planning_input.tariff.slot_prices),
        }
    )


st.title("⚡ VoltAI — Verified EV Fleet Charging Plan")
st.caption(
    "Fixture-backed demo. The coordinator only presents schedules accepted by an independent checker; "
    "approval is recorded locally and never controls chargers."
)

with st.sidebar:
    st.header("Planning priorities")
    cost_weight = st.slider("Cost", min_value=0, max_value=100, value=60, step=5)
    availability_weight = st.slider("Availability", min_value=0, max_value=100, value=30, step=5)
    health_weight = st.slider("Battery health", min_value=0, max_value=100, value=10, step=5)
    scenario_name = st.selectbox("Disruption scenario", list(EVENTS))
    st.divider()
    st.markdown("**Data mode:** cache-first fixture")
    st.caption("Refreshers reject invalid data and retain the last valid cache.")

planning_input = load_planning_input()
weights = ObjectiveWeights(cost_weight, availability_weight, health_weight)

try:
    result = coordinate_plan(planning_input, weights, event=EVENTS[scenario_name])
except ValueError as error:
    st.error(str(error))
    st.info("No schedule was generated because VoltAI will not guess a missing battery reading.")
    st.stop()

selected = result.selected
schedule = selected.schedule
checked = selected.check
active_input = result.planning_input
needs = calculate_all_energy_needs(active_input.vehicles, active_input.routes)
ready_count = sum(value <= 0 for value in schedule.unmet_energy_kwh.values())
total_energy = sum(schedule.delivered_energy_kwh.values())

metric_a, metric_b, metric_c, metric_d = st.columns(4)
metric_a.metric("Vehicles ready", f"{ready_count}/{len(active_input.vehicles)}")
metric_b.metric("Scheduled energy", f"{total_energy:.1f} kWh")
metric_c.metric("Verified energy cost", f"INR {checked.cost:.2f}")
metric_d.metric("Schedule status", "Verified" if checked.valid else "Blocked")

if checked.valid:
    st.success(result.explanation)
else:
    st.error(result.explanation)

st.caption(
    f"Tariff provenance: {result.data_status} · Source: {active_input.tariff.source} · "
    f"Fetched: {active_input.tariff.fetched_at}"
)

left, right = st.columns([1.2, 1])
with left:
    st.subheader("Scheduled charging load and tariff")
    chart_data = schedule_chart_data(active_input, schedule)
    base = alt.Chart(chart_data).encode(x=alt.X("Time:N", sort=None, title="30-minute slot"))
    load = base.mark_bar(color="#0ea5e9").encode(
        y=alt.Y("Charging load (kW):Q", title="Charging load (kW)"),
        tooltip=["Time", "Charging load (kW)", "Tariff (INR/kWh)"],
    )
    tariff = base.mark_line(color="#f59e0b", strokeWidth=3).encode(
        y=alt.Y("Tariff (INR/kWh):Q", title="Tariff (INR/kWh)"),
        tooltip=["Time", "Tariff (INR/kWh)"],
    )
    st.altair_chart(
        alt.layer(load, tariff).resolve_scale(y="independent").properties(height=340),
        use_container_width=True,
    )

with right:
    st.subheader("Checked proposals")
    proposal_rows = [
        {
            "Proposal": proposal.name.title(),
            "Verified": "Yes" if proposal.check.valid else "No",
            "Cost (INR)": proposal.check.cost,
            "Health penalty": proposal.schedule.objective["health_penalty"],
            "Unmet (kWh)": proposal.schedule.objective["unmet_energy_kwh"],
        }
        for proposal in result.proposals
    ]
    st.dataframe(pd.DataFrame(proposal_rows), hide_index=True, use_container_width=True)
    st.info(
        f"Selected: **{selected.name.title()}**. Numeric explanation grounding: "
        f"{'passed' if result.explanation_is_grounded else 'blocked'}."
    )

st.subheader("Fleet readiness and scheduled energy")
vehicle_rows = []
for vehicle in active_input.vehicles:
    need = needs[vehicle.vehicle_id]
    delivered = schedule.delivered_energy_kwh[vehicle.vehicle_id]
    vehicle_rows.append(
        {
            "Vehicle": vehicle.vehicle_id,
            "SOC": vehicle.soc_percent,
            "SOH": vehicle.soh_percent,
            "Temperature (°C)": vehicle.temperature_c,
            "Required (kWh)": need.required_charge_kwh,
            "Scheduled (kWh)": delivered,
            "Unmet (kWh)": schedule.unmet_energy_kwh[vehicle.vehicle_id],
            "Status": "Ready" if schedule.unmet_energy_kwh[vehicle.vehicle_id] <= 0 else "Needs operator decision",
        }
    )
st.dataframe(
    pd.DataFrame(vehicle_rows),
    hide_index=True,
    use_container_width=True,
    column_config={
        "SOC": st.column_config.ProgressColumn("SOC (%)", min_value=0, max_value=100, format="%.0f%%"),
        "SOH": st.column_config.ProgressColumn("SOH (%)", min_value=0, max_value=100, format="%.0f%%"),
    },
)

if not checked.valid:
    st.warning("Approval is disabled. Review the checker violations below and change the scenario or inputs.")
    st.dataframe(pd.DataFrame([item.__dict__ for item in checked.violations]), hide_index=True)
else:
    st.subheader("Human approval")
    operator = st.text_input("Operator name", placeholder="Required for the local approval record")
    if st.button("Approve verified plan", type="primary", disabled=not operator.strip()):
        destination = record_approval(
            schedule,
            operator=operator.strip(),
            destination=PROJECT_ROOT / "saved_outputs" / "approvals.jsonl",
        )
        st.success(f"Approval recorded in {destination.name}. No charger command was sent.")

st.divider()
st.caption(
    "Safety boundary: this application reads fixture/cache data, calculates a plan, and records explicit approval. "
    "It does not call live charging hardware, dispatch systems, or customer systems."
)
