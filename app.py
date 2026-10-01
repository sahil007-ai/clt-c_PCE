import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ==============================================================================
# 1. STREAMLIT PAGE CONFIGURATION & CUSTOM STYLING
# Wide layout, custom theme configured in .streamlit/config.toml
# ==============================================================================
st.set_page_config(
    page_title="VoltAI - AI Energy & EV Fleet Optimization System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Theme CSS Adjustments
st.markdown("""
<style>
    /* Metric Card Custom Styling */
    .metric-card {
        background: #1e293b;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #0ea5e9;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f8fafc;
        margin: 0.2rem 0;
    }
    .metric-sub {
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* AI Action Center Recommendation Box */
    .ai-callout {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border-left: 4px solid #0ea5e9;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .ai-badge {
        display: inline-block;
        background: rgba(14, 165, 233, 0.15);
        color: #0ea5e9;
        border: 1px solid rgba(14, 165, 233, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-bottom: 0.75rem;
    }
    .ai-text {
        font-size: 0.95rem;
        line-height: 1.6;
        color: #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SIDEBAR CONTROLS & MULTI-OBJECTIVE WEIGHT SLIDERS
# ==============================================================================
st.sidebar.markdown("## ⚙️ AI Optimization Parameters")
st.sidebar.markdown("Tune multi-objective weights to alter fleet charging strategy:")

cost_weight = st.sidebar.slider(
    "Cost Minimization Weight (%)",
    min_value=0, max_value=100, value=80, step=5,
    help="Prioritizes charging during cheap off-peak grid rate hours."
)

longevity_weight = st.sidebar.slider(
    "Battery Longevity Protection (%)",
    min_value=0, max_value=100, value=70, step=5,
    help="Caps fast-charging thermal stress and limits degradation."
)

turnaround_weight = st.sidebar.slider(
    "Fleet Turnaround Priority (%)",
    min_value=0, max_value=100, value=40, step=5,
    help="Prioritizes rapid charging to ensure route readiness."
)

st.sidebar.markdown("---")
st.sidebar.markdown("## 🚗 Fleet Telematics Filters")
min_soc = st.sidebar.slider(
    "Minimum SOC (%)",
    min_value=0, max_value=100, value=0, step=5,
    help="Filter vehicle telematics table by minimum State of Charge percentage."
)

# ==============================================================================
# 3. HEADER & TOP KPI METRICS
# ==============================================================================
st.title("⚡ VoltAI - AI Energy & EV Fleet Optimization System")
st.markdown("Real-time grid pricing load-shaping, battery telematics, and AI schedule control.")

# Top KPI Metric Cards Grid
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Total Fleet Size</div>
            <div class="metric-value">42 EVs</div>
            <div class="metric-sub" style="color: #10b981;">● 8 Monitored Vehicles</div>
        </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Current Grid Rate</div>
            <div class="metric-value" style="color: #f59e0b;">$0.48 / kWh</div>
            <div class="metric-sub" style="color: #f59e0b;">⚠️ Peak Pricing Window</div>
        </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Fleet Avg SOC</div>
            <div class="metric-value" style="color: #0ea5e9;">64%</div>
            <div class="metric-sub" style="color: #10b981;">↑ +3.8% vs last hour</div>
        </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown("""
        <div class="metric-card">
            <div class="metric-label">Projected Daily Cost</div>
            <div class="metric-value" style="color: #6366f1;">$1,280.50</div>
            <div class="metric-sub" style="color: #10b981;">↓ $385.00 AI Saved Today</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# 4. MAIN DASHBOARD CONTENT: TELEMATICS TABLE & ALTAIR CHART
# ==============================================================================
col_left, col_right = st.columns([1.15, 1])

# --- LEFT COLUMN: EV Telematics Data Table ---
with col_left:
    st.subheader("🚘 Live EV Telematics & Battery Health")

    # CRITICAL DATA FIX: Whole integers between 15 and 95 for SOC (%) and SOH (%)
    raw_telematics_data = [
        {"Vehicle ID": "EV-101", "Route": "Route 12 - Downtown Express", "SOC (%)": 35, "SOH (%)": 94, "Status": "Charging"},
        {"Vehicle ID": "EV-102", "Route": "Route 05 - Airport Shuttle",  "SOC (%)": 82, "SOH (%)": 98, "Status": "Ready / Standby"},
        {"Vehicle ID": "EV-103", "Route": "Route 08 - Metro North",     "SOC (%)": 18, "SOH (%)": 86, "Status": "Critical / Low SOC"},
        {"Vehicle ID": "EV-104", "Route": "Route 14 - Logistics Hub",    "SOC (%)": 65, "SOH (%)": 91, "Status": "Charging"},
        {"Vehicle ID": "EV-105", "Route": "Route 03 - Service Patrol",   "SOC (%)": 45, "SOH (%)": 88, "Status": "Throttled"},
        {"Vehicle ID": "EV-106", "Route": "Route 09 - Suburb Loop",      "SOC (%)": 92, "SOH (%)": 96, "Status": "Ready / Standby"},
        {"Vehicle ID": "EV-107", "Route": "Route 21 - Industrial Zone",  "SOC (%)": 28, "SOH (%)": 84, "Status": "Throttled"},
        {"Vehicle ID": "EV-108", "Route": "Route 04 - Cargo Depot",      "SOC (%)": 76, "SOH (%)": 93, "Status": "Charging"}
    ]

    df_telematics = pd.DataFrame(raw_telematics_data)

    # Filter dataframe by Minimum SOC (%) integer slider
    filtered_df = df_telematics[df_telematics["SOC (%)"] >= min_soc].copy()

    # Streamlit Dataframe with Progress Columns for SOC (%) and SOH (%)
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Vehicle ID": st.column_config.TextColumn("Vehicle ID", help="Unique EV Identifier"),
            "Route": st.column_config.TextColumn("Assigned Route"),
            "SOC (%)": st.column_config.ProgressColumn(
                "SOC (%)",
                help="State of Charge Percentage (0-100%)",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
            "SOH (%)": st.column_config.ProgressColumn(
                "SOH (%)",
                help="State of Health Percentage (0-100%)",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.TextColumn("Vehicle Status")
        }
    )

    if filtered_df.empty:
        st.info(f"No EV vehicles match the current Minimum SOC filter of {min_soc}%.")


# --- RIGHT COLUMN: Altair Dual-Axis Line & Bar Chart ---
with col_right:
    # CRITICAL UI FIX: Clean title "Draw vs. Grid Price Forecast"
    st.subheader("📊 Draw vs. Grid Price Forecast")

    # 12-Hour Timeline Data
    hours = ["12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00", "22:00", "23:00"]
    grid_prices = [0.18, 0.22, 0.26, 0.35, 0.48, 0.52, 0.46, 0.40, 0.30, 0.22, 0.15, 0.12]

    # Dynamic Charging Draw Logic tied to "Cost Minimization" slider
    charging_draw = []
    for price in grid_prices:
        if cost_weight > 50:
            if price >= 0.40:
                # Drop charging draw during peak price hours
                draw = int(250 * (1 - (cost_weight / 100)))
            else:
                # Shift charging draw to off-peak low price hours
                draw = int(180 + (cost_weight * 0.8))
        else:
            # High charging draw even during peak hours if cost minimization is low
            draw = 210

        charging_draw.append(max(10, draw))

    chart_data = pd.DataFrame({
        "Time": hours,
        "Grid Price ($/kWh)": grid_prices,
        "Charging Draw (kW)": charging_draw
    })

    # Altair Dual-Axis Chart Construction
    base = alt.Chart(chart_data).encode(x=alt.X('Time:N', sort=None, title='12-Hour Forecast Window'))

    # Bar Chart for Scheduled Charging Draw (kW) - Electric Blue theme (#0ea5e9)
    bar_chart = base.mark_bar(color='#0ea5e9', opacity=0.75, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y('Charging Draw (kW):Q', title='Charging Draw (kW)', scale=alt.Scale(domain=[0, 300])),
        tooltip=['Time', 'Charging Draw (kW)', 'Grid Price ($/kWh)']
    )

    # Line Chart for Grid Prices ($/kWh) - Warning Amber (#f59e0b)
    line_chart = base.mark_line(color='#f59e0b', strokeWidth=3, interpolate='monotone').encode(
        y=alt.Y('Grid Price ($/kWh):Q', title='Grid Price ($/kWh)', scale=alt.Scale(domain=[0, 0.60])),
        tooltip=['Time', 'Grid Price ($/kWh)']
    )

    points = base.mark_point(color='#f59e0b', size=45, filled=True).encode(
        y=alt.Y('Grid Price ($/kWh):Q')
    )

    # Combine charts with independent Y-axes
    dual_axis_chart = alt.layer(
        bar_chart,
        line_chart + points
    ).resolve_scale(
        y='independent'
    ).properties(
        height=330
    ).configure_view(
        strokeWidth=0
    ).configure_axis(
        labelColor='#94a3b8',
        titleColor='#94a3b8',
        gridColor='rgba(255, 255, 255, 0.05)'
    )

    st.altair_chart(dual_axis_chart, use_container_width=True)

# ==============================================================================
# 5. AI ACTION CENTER & RECOMMENDATION ENGINE
# ==============================================================================
st.markdown("---")
st.subheader("🤖 AI Action Center & Schedule Optimizer")

# Determine dominant slider weight
weights = {
    "Cost Minimization": cost_weight,
    "Battery Longevity": longevity_weight,
    "Fleet Turnaround": turnaround_weight
}
dominant_strategy = max(weights, key=weights.get)
dominant_value = weights[dominant_strategy]

# Generate Dynamic AI Recommendation Text based on dominant slider
if dominant_strategy == "Cost Minimization" and cost_weight >= 50:
    ai_recommendation = (
        f"Grid prices are currently peaking at **$0.52/kWh** between 16:00 and 19:00. With **Cost Minimization prioritized at {cost_weight}%**, "
        f"the AI engine has scheduled an aggressive peak-shaving policy. Fast chargers are throttled to 15 kW during peak hours, deferring "
        f"240 kW of load to 22:00 when grid prices plunge to **$0.12/kWh**. Projected nightly financial savings: **$425.00**."
    )
elif dominant_strategy == "Battery Longevity":
    ai_recommendation = (
        f"Telematics indicate cell temperatures of 41°C+ on EV-103 & EV-107. With **Battery Longevity Protection prioritized at {longevity_weight}%**, "
        f"the AI engine recommends enforcing a strict 40 kW charging rate cap and limiting maximum SOC dwell time above 85%. This prevents thermal degradation "
        f"and extends fleet battery pack lifetime by **+24%**."
    )
else:
    ai_recommendation = (
        f"Fleet turnaround demands are high for evening shuttles. With **Fleet Turnaround prioritized at {turnaround_weight}%**, "
        f"the AI engine recommends overriding off-peak deferrals to supply max 180 kW fast charging to EV-101, EV-103, and EV-104. "
        f"All units will reach 90% SOC by 18:30 for rapid route dispatch. Projected grid cost impact: **+$145.00**."
    )

# Render AI Callout Card
st.markdown(f"""
    <div class="ai-callout">
        <div class="ai-badge">✨ Live AI Recommendation (Strategy: {dominant_strategy} - {dominant_value}%)</div>
        <div class="ai-text">{ai_recommendation}</div>
    </div>
""", unsafe_allow_html=True)

# Action Accept Button
if st.button("Accept AI Schedule", use_container_width=True, type="primary"):
    st.success("✅ **AI Optimization Schedule Accepted!** Smart charger controllers, V2G inverters, and fleet dispatch schedules have been updated successfully.")
