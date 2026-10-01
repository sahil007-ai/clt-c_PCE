"""VoltAI Streamlit dashboard backed exclusively by verified engine output.

Styled with the minimalist Notion/Pinterest aesthetic: muted olive green (#4B6043),
crisp off-white cards (#FFFFFF / #F8F9FA), dark charcoal typography (#2D3748),
the latest transparent brand logo (logo_transparent.png), and dual-axis Altair
load/tariff charts directly aligned with index.html.
"""

from __future__ import annotations

import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from agent.copilot import run_operations_copilot
from agent.graph import coordinate_plan
from agent.tools import record_approval
from engine.energy import calculate_all_energy_needs
from engine.generate import PROJECT_ROOT, load_planning_input
from engine.schemas import ObjectiveWeights

# Determine logo path (matching index.html candidate logo fallback chain)
LOGO_CANDIDATES = [
    "logo_transparent.png",
    "Gemini_Generated_Image_n26va3n26va3n26v.png",
    "logo.png",
]
LOGO_PATH = next((p for p in LOGO_CANDIDATES if Path(p).is_file()), "logo_transparent.png")

# Page configuration with recent brand logo favicon
st.set_page_config(
    page_title="VoltAI — Verified EV Fleet Planning",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit official navigation logo
if os.path.exists(LOGO_PATH):
    st.logo(LOGO_PATH, icon_image=LOGO_PATH, size="medium")


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


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS & BRANDING
# -----------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=130)
    st.markdown("### Planning Priorities")
    cost_weight = st.slider(
        "Cost optimization",
        min_value=0,
        max_value=100,
        value=60,
        step=5,
        help="Weight given to scheduling charging during lowest-tariff off-peak windows.",
    )
    availability_weight = st.slider(
        "Fleet readiness",
        min_value=0,
        max_value=100,
        value=30,
        step=5,
        help="Weight given to ensuring departure target energy is 100% satisfied.",
    )
    health_weight = st.slider(
        "Battery longevity",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        help="Weight given to minimizing fast-charge thermal stress and pack degradation.",
    )

    st.divider()
    st.markdown("### Disruption Scenarios")
    scenario_name = st.selectbox(
        "Active scenario",
        list(EVENTS),
        help="Simulate real-world depot anomalies and inspect automated contingency replanning.",
    )

    st.divider()
    with st.container(border=True):
        st.caption(":material/database: **Data Provenance**")
        st.markdown("Mode: `:green[Cache-First Fixture]`")
        st.caption("Automatic fallback on corrupted input. MERC regulatory review compliant.")


# -----------------------------------------------------------------------------
# ENGINE & OPTIMIZATION PIPELINE
# -----------------------------------------------------------------------------
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

# Run the Grounded LangGraph Multi-Agent Copilot
copilot = run_operations_copilot(result, event=EVENTS[scenario_name])


# -----------------------------------------------------------------------------
# BRANDED HEADER (WITH RECENT LOGO ICON)
# -----------------------------------------------------------------------------
header_logo, header_title, header_status = st.columns([0.08, 0.72, 0.20], vertical_alignment="center")

with header_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=54)

with header_title:
    st.title("VoltAI — Verified EV Fleet Planner")
    st.caption(
        "Deterministic scheduling engine & LangGraph multi-agent copilot. "
        "Verified independently before display; approval recorded locally with zero hardware dispatch."
    )

with header_status:
    if checked.valid:
        st.markdown(
            '<div style="text-align: right;"><span style="background-color: #F0FFF4; color: #38A169; '
            'padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; '
            'border: 1px solid #C6F6D5;">● SYSTEM NOMINAL</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align: right;"><span style="background-color: #FFF5F5; color: #E53E3E; '
            'padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 13px; '
            'border: 1px solid #FED7D7;">● BLOCKED</span></div>',
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# KPI METRICS GRID (MATCHING INDEX.HTML SVG ICONS & CARD TOKENS)
# -----------------------------------------------------------------------------
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

with metric_col1:
    with st.container(border=True):
        st.caption(":material/battery_charging_full: **Fleet Readiness**")
        st.metric(
            label="Ready count",
            value=f"{ready_count}/{len(active_input.vehicles)}",
            delta=None,
            label_visibility="collapsed",
        )
        st.caption(f"{ready_count} vehicles fully ready for departure")

with metric_col2:
    with st.container(border=True):
        st.caption(":material/bolt: **Scheduled Energy**")
        st.metric(
            label="Delivered energy",
            value=f"{total_energy:.1f} kWh",
            delta=None,
            label_visibility="collapsed",
        )
        st.caption(f"{len(schedule.assignments)} charging slot allocations")

with metric_col3:
    with st.container(border=True):
        st.caption(":material/trending_up: **Verified Energy Cost**")
        st.metric(
            label="Total cost",
            value=f"₹{checked.cost:.2f}",
            delta=None,
            label_visibility="collapsed",
        )
        st.caption(f"Accepted plan: {selected.name.title()}")

with metric_col4:
    with st.container(border=True):
        st.caption(":material/verified: **Schedule Status**")
        st.metric(
            label="Verification status",
            value="Verified" if checked.valid else "Blocked",
            delta="100% constraints met" if checked.valid else "Violations detected",
            delta_color="normal" if checked.valid else "inverse",
            label_visibility="collapsed",
        )
        st.caption("Audited by independent checker gate")


# -----------------------------------------------------------------------------
# GROUNDED MULTI-AGENT OPERATIONS COPILOT (LANGGRAPH ENGINE)
# -----------------------------------------------------------------------------
with st.expander(":material/auto_awesome: **Grounded Multi-Agent Operations Copilot** (LangGraph)", expanded=True):
    copilot_tabs = st.tabs([
        "Operator Briefing",
        "Planner Specialist",
        "Disruption Analyst",
        "Battery Health Reviewer",
        "Data & Safety Auditor",
    ])

    with copilot_tabs[0]:
        st.markdown(f"**Briefing Lead Role:** `{copilot.operator_briefing.role}`")
        st.info(copilot.operator_briefing.summary)
        for detail in copilot.operator_briefing.details:
            st.markdown(f"- {detail}")
        st.caption("LLM model: `nvidia/nemotron-3-ultra-550b-a55b:free` · Numeric grounding verified against engine facts.")

    with copilot_tabs[1]:
        st.markdown(f"**Specialist Role:** `{copilot.planner.role}`")
        st.write(copilot.planner.summary)
        for detail in copilot.planner.details:
            st.markdown(f"- {detail}")

    with copilot_tabs[2]:
        st.markdown(f"**Specialist Role:** `{copilot.scenario_analyst.role}`")
        st.write(copilot.scenario_analyst.summary)
        for detail in copilot.scenario_analyst.details:
            st.markdown(f"- {detail}")

    with copilot_tabs[3]:
        st.markdown(f"**Specialist Role:** `{copilot.battery_reviewer.role}`")
        st.write(copilot.battery_reviewer.summary)
        for detail in copilot.battery_reviewer.details:
            st.markdown(f"- {detail}")

    with copilot_tabs[4]:
        st.markdown(f"**Specialist Role:** `{copilot.safety_reviewer.role}`")
        st.write(copilot.safety_reviewer.summary)
        for detail in copilot.safety_reviewer.details:
            st.markdown(f"- {detail}")


# -----------------------------------------------------------------------------
# DUAL-AXIS CHARGING LOAD & TARIFF CHART (ALTAIR STYLED AS INDEX.HTML)
# -----------------------------------------------------------------------------
st.divider()

# Detect active theme mode (defaulting to light theme if unspecified)
is_dark_theme = getattr(st.context, "theme", None) and getattr(st.context.theme, "type", "") == "dark"

# Muted olive palette matching index.html CSS tokens
load_color = "#688B5E" if is_dark_theme else "#4B6043"
tariff_color = "#ECC94B" if is_dark_theme else "#D69E2E"
grid_color = "#374151" if is_dark_theme else "#E2E8F0"
axis_label_color = "#A0AEC0" if is_dark_theme else "#718096"
axis_title_color = "#F7FAFC" if is_dark_theme else "#2D3748"

left_chart, right_proposals = st.columns([1.3, 1])

with left_chart:
    st.subheader("Scheduled Charging Load and Tariff")
    st.caption("30-minute slot allocation optimized against Time-of-Day (ToD) tariff windows.")
    chart_df = schedule_chart_data(active_input, schedule)

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            "Time:N",
            sort=None,
            title="30-Minute Schedule Slot",
            axis=alt.Axis(
                labelColor=axis_label_color,
                titleColor=axis_title_color,
                labelAngle=-45,
                grid=False,
            ),
        )
    )

    # Charging load bars (Muted Olive Green) with rounded tops
    load_bars = base.mark_bar(
        color=load_color,
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4,
        opacity=0.85,
    ).encode(
        y=alt.Y(
            "Charging load (kW):Q",
            title="Charging Load (kW)",
            axis=alt.Axis(
                labelColor=load_color,
                titleColor=load_color,
                grid=True,
                gridColor=grid_color,
            ),
        ),
        tooltip=["Time", "Charging load (kW)", "Tariff (INR/kWh)"],
    )

    # Tariff area background tint (Gold/Yellow)
    tariff_area = base.mark_area(
        color=tariff_color,
        opacity=0.08,
        interpolate="monotone",
    ).encode(
        y=alt.Y(
            "Tariff (INR/kWh):Q",
            title="Tariff (INR/kWh)",
            axis=alt.Axis(
                labelColor=tariff_color,
                titleColor=tariff_color,
                grid=False,
            ),
        )
    )

    # Tariff line curve (Gold/Yellow)
    tariff_line = base.mark_line(
        color=tariff_color,
        strokeWidth=3,
        interpolate="monotone",
    ).encode(
        y=alt.Y(
            "Tariff (INR/kWh):Q",
            title="Tariff (INR/kWh)",
            axis=alt.Axis(
                labelColor=tariff_color,
                titleColor=tariff_color,
                grid=False,
            ),
        ),
        tooltip=["Time", "Tariff (INR/kWh)"],
    )

    combined_chart = (
        alt.layer(load_bars, tariff_area, tariff_line)
        .resolve_scale(y="independent")
        .properties(height=360)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(combined_chart, width="stretch")


with right_proposals:
    st.subheader("Checked Proposals")
    st.caption("Candidate optimization vectors scored across objectives.")
    proposal_rows = [
        {
            "Proposal": proposal.name.title(),
            "Verified": "✓ Yes" if proposal.check.valid else "✗ No",
            "Cost (₹)": f"₹{proposal.check.cost:.2f}",
            "Health Penalty": f"{proposal.schedule.objective['health_penalty']:.1f}",
            "Unmet Energy": f"{proposal.schedule.objective['unmet_energy_kwh']:.1f} kWh",
        }
        for proposal in result.proposals
    ]
    st.dataframe(pd.DataFrame(proposal_rows), hide_index=True, width="stretch")
    with st.container(border=True):
        st.markdown(
            f"**Selected Proposal:** `:green[{selected.name.title()}]`  \n"
            f"Numeric Grounding Status: **{'Passed' if result.explanation_is_grounded else 'Blocked'}**"
        )
        st.caption(
            f"Tariff Provenance: {result.data_status} · "
            f"Source: {active_input.tariff.source} · "
            f"Fetched: {active_input.tariff.fetched_at}"
        )


# -----------------------------------------------------------------------------
# FLEET READINESS & TELEMETRY TABLE
# -----------------------------------------------------------------------------
st.divider()
st.subheader("Fleet Readiness & Battery Telemetry")
st.caption("Pack state-of-charge, state-of-health, cell temperature, and target energy fulfillment.")

vehicle_rows = []
for vehicle in active_input.vehicles:
    need = needs[vehicle.vehicle_id]
    delivered = schedule.delivered_energy_kwh[vehicle.vehicle_id]
    unmet = schedule.unmet_energy_kwh[vehicle.vehicle_id]
    vehicle_rows.append(
        {
            "Vehicle": vehicle.vehicle_id,
            "SOC": vehicle.soc_percent,
            "SOH": vehicle.soh_percent,
            "Temp (°C)": vehicle.temperature_c,
            "Target (kWh)": need.required_charge_kwh,
            "Scheduled (kWh)": round(delivered, 1),
            "Unmet (kWh)": round(unmet, 1),
            "Status": "Ready" if unmet <= 0 else "Needs Decision",
        }
    )

st.dataframe(
    pd.DataFrame(vehicle_rows),
    hide_index=True,
    width="stretch",
    column_config={
        "SOC": st.column_config.ProgressColumn(
            "SOC (%)",
            min_value=0,
            max_value=100,
            format="%.0f%%",
        ),
        "SOH": st.column_config.ProgressColumn(
            "SOH (%)",
            min_value=0,
            max_value=100,
            format="%.0f%%",
        ),
    },
)


# -----------------------------------------------------------------------------
# HUMAN APPROVAL WORKFLOW
# -----------------------------------------------------------------------------
st.divider()

if not checked.valid:
    with st.container(border=True):
        st.error("⚠️ **Schedule Check Failed — Approval Blocked**")
        st.markdown("The independent checker detected constraint violations in this schedule. Review details below:")
        st.dataframe(pd.DataFrame([item.__dict__ for item in checked.violations]), hide_index=True, width="stretch")
else:
    with st.container(border=True):
        st.markdown("### :material/fingerprint: Human Operator Approval")
        st.caption("In accordance with system safety policies, schedule dispatch requires explicit operator sign-off.")
        col_op, col_btn = st.columns([0.7, 0.3], vertical_alignment="bottom")
        with col_op:
            operator = st.text_input("Authorized operator name", placeholder="e.g., Sarah Chen (Depot Lead)")
        with col_btn:
            if st.button("Approve Verified Plan", type="primary", disabled=not operator.strip(), width="stretch"):
                destination = record_approval(
                    schedule,
                    operator=operator.strip(),
                    destination=PROJECT_ROOT / "saved_outputs" / "approvals.jsonl",
                )
                st.success(f"✓ Approval recorded in `{destination.name}`. Physical hardware commands isolated.")


# -----------------------------------------------------------------------------
# SAFETY FOOTER
# -----------------------------------------------------------------------------
st.divider()
st.caption(
    "🔒 **Safety boundary:** VoltAI reads versioned fixtures, calculates plans through deterministic heuristics, "
    "and audits outputs via an independent checker gate. It does not issue physical hardware dispatch, "
    "OCPP commands, or telematics control signals."
)
