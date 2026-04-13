"""
Program IQ – Urban Arts Intelligence Dashboard
Main Streamlit application entry point.
"""
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ─────────────────────────────
st.set_page_config(
    page_title="Program IQ – Urban Arts",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #0F0F1A;
    color: #F1F5F9;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #1A1A2E !important;
    border-right: 1px solid #334155;
}

[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #94A3B8 !important;
}

/* ── Metric cards ── */
div[data-testid="metric-container"] {
    background: #1E1E30;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px 20px;
    transition: transform 0.15s;
}
div[data-testid="metric-container"]:hover {
    transform: translateY(-2px);
    border-color: #FF6B35;
}

div[data-testid="metric-container"] label {
    color: #94A3B8 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #F1F5F9 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}

/* ── Section headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #FF6B35;
    border-left: 3px solid #FF6B35;
    padding-left: 10px;
    margin: 24px 0 12px 0;
}

/* ── Cards ── */
.card {
    background: #1E1E30;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
}

/* ── Insight bullets ── */
.insight-item {
    background: linear-gradient(135deg, #1E1E30, #2A2A3E);
    border-left: 3px solid #7C3AED;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 0.93rem;
    color: #E2E8F0;
    line-height: 1.5;
}

/* ── Risk badges ── */
.badge-high {
    background: #7F1D1D;
    color: #FCA5A5;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-medium {
    background: #78350F;
    color: #FCD34D;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-ok {
    background: #064E3B;
    color: #6EE7B7;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* ── Data table ── */
.dataframe {
    background: #1E1E30 !important;
    color: #F1F5F9 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #1E1E30;
    border-radius: 10px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #94A3B8;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: #FF6B35 !important;
    color: white !important;
}

/* ── Text input / query bar ── */
.stTextInput input {
    background: #1E1E30 !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    color: #F1F5F9 !important;
    font-size: 1rem !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #FF6B35 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.5rem !important;
    transition: opacity 0.15s !important;
}
.stButton > button:hover {
    opacity: 0.85 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1E1E30;
    border: 1px solid #334155;
    border-radius: 10px;
}

/* ── Plotly charts ── */
.js-plotly-plot .plotly {
    border-radius: 10px;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: #1E1E30 !important;
    border: 1px solid #7C3AED !important;
    color: #A78BFA !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Data loading ───────────────────────────────────────────────────────────
from modules.data_loader import load_attendance, load_work, load_yearly, get_date_columns
from modules.data_transformer import (
    build_long_attendance,
    build_session_trend,
    generate_demographics,
)
from modules.analytics import (
    overview_metrics,
    student_performance_table,
    at_risk_students,
    team_performance,
    attendance_distribution,
    late_vs_absent_correlation,
    yearly_enrollment_trend,
    role_distribution,
    art_vs_programming,
)
from modules.visualizations import (
    session_attendance_chart,
    attendance_distribution_chart,
    team_performance_chart,
    late_absent_scatter,
    role_distribution_chart,
    art_vs_programming_chart,
    yearly_enrollment_chart,
    status_donut,
    student_sparkline,
)
from modules.ai_engine import generate_insights, process_nl_query
from modules.exports import generate_pdf
from utils.constants import COLORS, PROGRAM_DATA


@st.cache_data(ttl=3600, show_spinner=False)
def load_all():
    df_att = load_attendance()
    df_work = load_work()
    enroll_df, retain_df = load_yearly()
    df_long = build_long_attendance(df_att)
    df_session = build_session_trend(df_att)
    demographics = generate_demographics(list(df_att["student_id"].unique()))
    df_perf = student_performance_table(df_att, df_work)
    return {
        "att": df_att,
        "work": df_work,
        "long": df_long,
        "session": df_session,
        "enroll": enroll_df,
        "retain": retain_df,
        "demographics": demographics,
        "perf": df_perf,
    }


# ── Load with spinner ──────────────────────────────────────────────────────
with st.spinner("Loading Program IQ…"):
    try:
        data = load_all()
        load_error = None
    except Exception as e:
        data = None
        load_error = str(e)


# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 16px 0 8px 0;">
            <div style="font-size:2.2rem;">🎮</div>
            <div style="font-size:1.3rem; font-weight:700; color:#FF6B35;">Program IQ</div>
            <div style="font-size:0.78rem; color:#64748B; margin-top:2px;">Urban Arts Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    page = st.selectbox(
        "Navigate",
        [
            "📊 Overview",
            "👥 Student Performance",
            "🏆 Team Analysis",
            "⚠️ At-Risk Students",
            "📈 Program Trends",
            "🤖 AI Query",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    if data:
        metrics = overview_metrics(data["att"], data["session"])
        st.markdown("**Quick Stats**")
        st.markdown(
            f"""
            <div style="font-size:0.82rem; color:#94A3B8; line-height:2;">
            🎓 {metrics['total_students']} active students<br>
            📅 {metrics['sessions']} sessions recorded<br>
            ✅ {metrics['avg_attendance']:.1f}% avg attendance<br>
            🔴 {metrics['low_performers']} need attention
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.warning("Set ANTHROPIC_API_KEY in .env for AI features", icon="🔑")
    else:
        st.success("AI Insights enabled", icon="✅")

    st.caption("Program IQ v2.0  ·  Urban Arts")


# ── Error state ────────────────────────────────────────────────────────────
if load_error:
    st.error(f"Failed to load data: {load_error}")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════
if page == "📊 Overview":
    st.markdown(
        "<h1 style='color:#FF6B35; margin-bottom:4px;'>📊 Program Overview</h1>"
        "<p style='color:#64748B; margin-top:0;'>Urban Arts · 3D Game Design · 2025/26 School Year</p>",
        unsafe_allow_html=True,
    )

    metrics = overview_metrics(data["att"], data["session"])

    # ── KPI Row ───────────────────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Students", metrics["total_students"])
    col2.metric(
        "Avg Attendance",
        f"{metrics['avg_attendance']:.1f}%",
        delta=f"Last session {metrics['recent_session_rate']:.0f}%",
    )
    col3.metric("Sessions Recorded", metrics["sessions"])
    col4.metric("High Performers (≥90%)", metrics["high_performers"])
    col5.metric(
        "Need Attention (<70%)",
        metrics["low_performers"],
        delta=f"{metrics['critical_students']} critical",
        delta_color="inverse",
    )

    st.markdown('<div class="section-header">Attendance Over Time</div>', unsafe_allow_html=True)

    # ── Session Trend + Donut ──────────────────────────────────────────────
    left, right = st.columns([3, 1])
    with left:
        st.plotly_chart(
            session_attendance_chart(data["session"]),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            status_donut(data["session"]),
            use_container_width=True,
        )

    # ── Distribution + AI Insights ────────────────────────────────────────
    left2, right2 = st.columns([1, 1])
    with left2:
        st.markdown('<div class="section-header">Attendance Distribution</div>', unsafe_allow_html=True)
        dist = attendance_distribution(data["att"])
        st.plotly_chart(
            attendance_distribution_chart(dist),
            use_container_width=True,
        )

    with right2:
        st.markdown('<div class="section-header">🤖 AI Insights</div>', unsafe_allow_html=True)
        with st.spinner("Generating insights…"):
            insights = generate_insights(data["att"], data["work"])

        for insight in insights:
            st.markdown(
                f'<div class="insight-item">💡 {insight}</div>',
                unsafe_allow_html=True,
            )

    # ── Programs at a Glance ──────────────────────────────────────────────
    st.markdown('<div class="section-header">Programs at a Glance</div>', unsafe_allow_html=True)
    prog_cols = st.columns(4)
    for i, prog in enumerate(PROGRAM_DATA[:4]):
        with prog_cols[i]:
            pct = round(prog["retention"] * 100)
            color = "#10B981" if pct >= 85 else "#F59E0B" if pct >= 70 else "#EF4444"
            st.markdown(
                f"""
                <div class="card">
                    <div style="font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em;">{prog['type']}</div>
                    <div style="font-size:1rem; font-weight:600; color:#F1F5F9; margin:4px 0;">{prog['name']}</div>
                    <div style="font-size:1.6rem; font-weight:700; color:{color};">{pct}%</div>
                    <div style="font-size:0.78rem; color:#64748B;">retention · {prog['enrolled_2024']} enrolled</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    prog_cols2 = st.columns(4)
    for i, prog in enumerate(PROGRAM_DATA[4:]):
        with prog_cols2[i]:
            pct = round(prog["retention"] * 100)
            color = "#10B981" if pct >= 85 else "#F59E0B" if pct >= 70 else "#EF4444"
            st.markdown(
                f"""
                <div class="card">
                    <div style="font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em;">{prog['type']}</div>
                    <div style="font-size:1rem; font-weight:600; color:#F1F5F9; margin:4px 0;">{prog['name']}</div>
                    <div style="font-size:1.6rem; font-weight:700; color:{color};">{pct}%</div>
                    <div style="font-size:0.78rem; color:#64748B;">retention · {prog['enrolled_2024']} enrolled</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: STUDENT PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════
elif page == "👥 Student Performance":
    st.markdown(
        "<h1 style='color:#FF6B35;'>👥 Student Performance</h1>",
        unsafe_allow_html=True,
    )

    df_perf = data["perf"].copy()

    # ── Filters ───────────────────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3 = st.columns(3)
        min_att, max_att = fc1.slider("Attendance Range (%)", 0, 100, (0, 100), step=5)
        teams = ["All"] + sorted(
            [t for t in df_perf["Project Team Name"].dropna().unique() if t]
        )
        team_filter = fc2.selectbox("Project Team", teams)
        sort_by = fc3.selectbox(
            "Sort By",
            ["Attendance % ↑", "Attendance % ↓", "Absences ↑", "Missing Work ↑"],
        )

    # Apply filters
    mask = (df_perf["Attendance %"] >= min_att) & (df_perf["Attendance %"] <= max_att)
    if team_filter != "All":
        mask &= df_perf["Project Team Name"] == team_filter
    df_filtered = df_perf[mask].copy()

    sort_map = {
        "Attendance % ↑": ("Attendance %", True),
        "Attendance % ↓": ("Attendance %", False),
        "Absences ↑": ("Absent", False),
        "Missing Work ↑": ("% missing_num", False),
    }
    scol, sasc = sort_map[sort_by]
    df_filtered = df_filtered.sort_values(scol, ascending=sasc)

    st.markdown(
        f'<div class="section-header">Student Roster — {len(df_filtered)} students</div>',
        unsafe_allow_html=True,
    )

    # ── Student Table ─────────────────────────────────────────────────────
    display_cols = [
        "First Name", "Last Name", "Attendance %", "Present", "Late",
        "Absent", "% good_num", "% missing_num", "Project Team Name",
        "Project Team Role", "Priority",
    ]
    show_cols = [c for c in display_cols if c in df_filtered.columns]
    table_df = df_filtered[show_cols].copy()

    # Format numerics
    if "Attendance %" in table_df.columns:
        table_df["Attendance %"] = table_df["Attendance %"].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
        )
    if "% good_num" in table_df.columns:
        table_df = table_df.rename(columns={"% good_num": "Work Quality"})
        table_df["Work Quality"] = table_df["Work Quality"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "—"
        )
    if "% missing_num" in table_df.columns:
        table_df = table_df.rename(columns={"% missing_num": "Missing Work"})
        table_df["Missing Work"] = table_df["Missing Work"].apply(
            lambda x: f"{x:.0f}%" if pd.notna(x) else "—"
        )

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Priority": st.column_config.TextColumn("Priority", width="small"),
        },
    )

    # ── Student Detail Drilldown ─────────────────────────────────────────
    st.markdown('<div class="section-header">Student Attendance Timeline</div>', unsafe_allow_html=True)

    student_names = [
        f"{r['First Name']} {r['Last Name']}"
        for _, r in data["perf"].iterrows()
    ]
    selected_name = st.selectbox("Select a student", student_names)
    if selected_name:
        selected_row = data["perf"][
            data["perf"]["First Name"] + " " + data["perf"]["Last Name"] == selected_name
        ].iloc[0]
        sid = selected_row["student_id"]

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Attendance", f"{selected_row['Attendance %']:.1f}%")
        sc2.metric("Absences", int(selected_row["Absent"]))
        sc3.metric("Late Arrivals", int(selected_row["Late"]))
        sc4.metric(
            "Team",
            str(selected_row.get("Project Team Name", "—") or "—"),
        )

        sparkline = student_sparkline(data["long"], sid)
        st.markdown("**Session-by-session attendance:**")
        st.plotly_chart(sparkline, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: TEAM ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
elif page == "🏆 Team Analysis":
    st.markdown(
        "<h1 style='color:#FF6B35;'>🏆 Team Analysis</h1>",
        unsafe_allow_html=True,
    )

    df_teams = team_performance(data["perf"])

    if df_teams.empty:
        st.info("No team data available.")
    else:
        # ── Team KPIs ─────────────────────────────────────────────────────
        top_team = df_teams.iloc[0]
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Teams Active", len(df_teams))
        tc2.metric(
            "Best Attendance",
            f"{top_team['Avg_Attendance']:.1f}%",
            delta=str(top_team["Project Team Name"]),
        )
        best_work_idx = df_teams["Avg_Good"].idxmax()
        tc3.metric(
            "Best Work Quality",
            f"{df_teams.loc[best_work_idx, 'Avg_Good']:.1f}%",
            delta=str(df_teams.loc[best_work_idx, "Project Team Name"]),
        )
        total_students = df_teams["Students"].sum()
        tc4.metric("Students in Teams", int(total_students))

        st.markdown('<div class="section-header">Team Performance Comparison</div>', unsafe_allow_html=True)
        st.plotly_chart(team_performance_chart(df_teams), use_container_width=True)

        # ── Team Detail Cards ─────────────────────────────────────────────
        st.markdown('<div class="section-header">Team Breakdown</div>', unsafe_allow_html=True)
        team_col_n = min(len(df_teams), 3)
        team_cols = st.columns(team_col_n)
        for i, (_, row) in enumerate(df_teams.iterrows()):
            with team_cols[i % team_col_n]:
                att_color = (
                    "#10B981" if row["Avg_Attendance"] >= 85
                    else "#F59E0B" if row["Avg_Attendance"] >= 70
                    else "#EF4444"
                )
                st.markdown(
                    f"""
                    <div class="card">
                        <div style="font-size:1.1rem;font-weight:700;color:#F1F5F9;">{row['Project Team Name']}</div>
                        <div style="font-size:0.8rem;color:#64748B;margin-bottom:8px;">{int(row['Students'])} students</div>
                        <div style="display:flex;gap:16px;margin-top:8px;">
                            <div>
                                <div style="font-size:1.4rem;font-weight:700;color:{att_color};">{row['Avg_Attendance']:.1f}%</div>
                                <div style="font-size:0.72rem;color:#64748B;">Attendance</div>
                            </div>
                            <div>
                                <div style="font-size:1.4rem;font-weight:700;color:#7C3AED;">{row['Avg_Good']:.1f}%</div>
                                <div style="font-size:0.72rem;color:#64748B;">Work Quality</div>
                            </div>
                            <div>
                                <div style="font-size:1.4rem;font-weight:700;color:#EF4444;">{row['Avg_Missing']:.1f}%</div>
                                <div style="font-size:0.72rem;color:#64748B;">Missing</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Role & Track Distribution ─────────────────────────────────────────
    st.markdown('<div class="section-header">Role & Track Distribution</div>', unsafe_allow_html=True)
    rc1, rc2 = st.columns(2)

    with rc1:
        df_roles = role_distribution(data["work"])
        if not df_roles.empty:
            st.plotly_chart(role_distribution_chart(df_roles), use_container_width=True)

    with rc2:
        df_track = art_vs_programming(data["work"])
        if not df_track.empty:
            st.plotly_chart(art_vs_programming_chart(df_track), use_container_width=True)

    # ── Late vs Absent Correlation ────────────────────────────────────────
    st.markdown('<div class="section-header">Late Arrivals vs Absences</div>', unsafe_allow_html=True)
    corr_data = late_vs_absent_correlation(data["att"])
    st.plotly_chart(late_absent_scatter(corr_data), use_container_width=True)
    if corr_data["corr"] is not None:
        r = corr_data["corr"]
        strength = "strong" if abs(r) > 0.6 else "moderate" if abs(r) > 0.3 else "weak"
        st.caption(
            f"Correlation r={r} ({strength} positive relationship). "
            "Students with more late arrivals tend to accumulate more absences."
        )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AT-RISK STUDENTS
# ══════════════════════════════════════════════════════════════════════════
elif page == "⚠️ At-Risk Students":
    st.markdown(
        "<h1 style='color:#EF4444;'>⚠️ At-Risk Students</h1>",
        unsafe_allow_html=True,
    )

    df_at_risk = at_risk_students(data["perf"])

    # ── Summary ───────────────────────────────────────────────────────────
    high = (df_at_risk["Priority"] == "HIGH").sum()
    med = (df_at_risk["Priority"] == "MEDIUM").sum()

    ac1, ac2, ac3, ac4 = st.columns(4)
    ac1.metric("Total At-Risk", len(df_at_risk), delta="need outreach", delta_color="off")
    ac2.metric("HIGH Priority", int(high), delta="immediate action", delta_color="inverse")
    ac3.metric("MEDIUM Priority", int(med), delta="monitor closely", delta_color="off")
    ac4.metric(
        "% of Class",
        f"{len(df_at_risk)/len(data['perf'])*100:.0f}%",
        delta_color="off",
    )

    st.markdown(
        """
        <div style="background:#1E1E30; border:1px solid #334155; border-radius:10px; padding:12px 16px; margin:12px 0; font-size:0.88rem; color:#94A3B8;">
        <b style="color:#F59E0B;">At-Risk Criteria:</b>
        Attendance &lt;70% <b>OR</b> Missing work &gt;50% <b>OR</b> Absences &gt;8
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df_at_risk.empty:
        st.success("No at-risk students detected! All students are meeting attendance benchmarks.")
    else:
        for _, row in df_at_risk.iterrows():
            priority = row.get("Priority", "OK")
            badge_class = f"badge-{priority.lower()}"
            name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
            att = row.get("Attendance %", 0)
            absent = int(row.get("Absent", 0))
            late = int(row.get("Late", 0))
            missing = row.get("% missing_num") or 0
            team = str(row.get("Project Team Name") or "—")

            border_color = "#7F1D1D" if priority == "HIGH" else "#78350F"

            st.markdown(
                f"""
                <div style="background:#1E1E30; border:1px solid {border_color}; border-radius:10px; padding:14px 18px; margin-bottom:10px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span style="font-size:1rem; font-weight:600; color:#F1F5F9;">{name}</span>
                        <span style="margin-left:10px;"><span class="{badge_class}">{priority}</span></span>
                        <div style="font-size:0.8rem; color:#64748B; margin-top:4px;">Team: {team}</div>
                    </div>
                    <div style="display:flex; gap:24px; flex-wrap:wrap;">
                        <div style="text-align:center;">
                            <div style="font-size:1.2rem; font-weight:700; color:#EF4444;">{att:.1f}%</div>
                            <div style="font-size:0.72rem; color:#64748B;">Attendance</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:1.2rem; font-weight:700; color:#F59E0B;">{absent}</div>
                            <div style="font-size:0.72rem; color:#64748B;">Absences</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:1.2rem; font-weight:700; color:#F97316;">{late}</div>
                            <div style="font-size:0.72rem; color:#64748B;">Late</div>
                        </div>
                        <div style="text-align:center;">
                            <div style="font-size:1.2rem; font-weight:700; color:#8B5CF6;">{missing:.0f}%</div>
                            <div style="font-size:0.72rem; color:#64748B;">Missing Work</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Export ────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Export Report**")
    if st.button("Generate PDF Report"):
        with st.spinner("Generating PDF…"):
            metrics_for_pdf = overview_metrics(data["att"], data["session"])
            df_teams_pdf = team_performance(data["perf"])
            insights_pdf = generate_insights(data["att"], data["work"])
            session_fig = session_attendance_chart(data["session"])
            pdf_bytes = generate_pdf(
                metrics_for_pdf, data["perf"], df_teams_pdf, insights_pdf, session_fig
            )

        if pdf_bytes:
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name="urban_arts_program_report.pdf",
                mime="application/pdf",
            )
        else:
            st.warning("PDF generation requires the fpdf2 package. Run: `pip install fpdf2`")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: PROGRAM TRENDS
# ══════════════════════════════════════════════════════════════════════════
elif page == "📈 Program Trends":
    st.markdown(
        "<h1 style='color:#FF6B35;'>📈 Program Trends</h1>",
        unsafe_allow_html=True,
    )

    # ── Yearly enrollment ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">Multi-Year Enrollment by Program</div>', unsafe_allow_html=True)
    enroll_trend = yearly_enrollment_trend(data["enroll"])
    if not enroll_trend.empty:
        st.plotly_chart(yearly_enrollment_chart(enroll_trend), use_container_width=True)
    else:
        st.info("Enrollment trend data not available.")

    # ── Retention table ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">Retention Rates by Program</div>', unsafe_allow_html=True)

    if not data["retain"].empty:
        st.dataframe(data["retain"], use_container_width=True, hide_index=True)
    else:
        # Fall back to constants data
        prog_df = pd.DataFrame(PROGRAM_DATA)
        prog_df["Retention %"] = (prog_df["retention"] * 100).round(0).astype(int).astype(str) + "%"
        prog_df = prog_df.rename(columns={
            "name": "Program", "type": "Type",
            "enrolled_2024": "Enrolled 2024/25",
            "completed_2024": "Completed 2024/25",
        })
        st.dataframe(
            prog_df[["Program", "Type", "Enrolled 2024/25", "Completed 2024/25", "Retention %"]],
            use_container_width=True,
            hide_index=True,
        )

    # ── Key Stats Summary ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">Historical Highlights</div>', unsafe_allow_html=True)
    hc1, hc2, hc3 = st.columns(3)

    with hc1:
        st.markdown(
            """
            <div class="card">
                <div style="font-size:2rem; font-weight:800; color:#10B981;">668</div>
                <div style="font-size:0.9rem; color:#94A3B8;">Total Students 2024/25</div>
                <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">Across all programs</div>
            </div>
            """, unsafe_allow_html=True
        )
    with hc2:
        st.markdown(
            """
            <div class="card">
                <div style="font-size:2rem; font-weight:800; color:#FF6B35;">+55%</div>
                <div style="font-size:0.9rem; color:#94A3B8;">3D Game Dev Growth</div>
                <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">2023/24 → 2024/25</div>
            </div>
            """, unsafe_allow_html=True
        )
    with hc3:
        st.markdown(
            """
            <div class="card">
                <div style="font-size:2rem; font-weight:800; color:#7C3AED;">93%</div>
                <div style="font-size:0.9rem; color:#94A3B8;">Summer Core Retention</div>
                <div style="font-size:0.78rem; color:#64748B; margin-top:4px;">2024/25 · Best program</div>
            </div>
            """, unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AI QUERY
# ══════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Query":
    st.markdown(
        "<h1 style='color:#FF6B35;'>🤖 Natural Language Query</h1>"
        "<p style='color:#64748B;'>Ask questions about your data in plain English.</p>",
        unsafe_allow_html=True,
    )

    # ── Example queries ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">Example Queries</div>', unsafe_allow_html=True)
    examples = [
        "Which students have perfect attendance?",
        "Show me students who are at risk",
        "Who has the most late arrivals?",
        "What is the average attendance per team?",
        "Which students are missing the most work?",
    ]
    cols = st.columns(len(examples))
    clicked_example = None
    for col, ex in zip(cols, examples):
        if col.button(ex, use_container_width=True):
            clicked_example = ex

    st.divider()

    # ── Query input ───────────────────────────────────────────────────────
    query = st.text_input(
        "Ask a question:",
        value=clicked_example or "",
        placeholder="e.g. Who needs intervention?",
        label_visibility="collapsed",
    )

    if query:
        with st.spinner("Processing query…"):
            result = process_nl_query(query, data["att"], data["work"])

        if result.get("error"):
            st.error(result["error"])
        else:
            # Explanation
            if result.get("explanation"):
                st.markdown(
                    f'<div class="insight-item">💡 {result["explanation"]}</div>',
                    unsafe_allow_html=True,
                )

            # Show data
            res = result.get("result")
            viz_type = result.get("viz_type", "table")
            config = result.get("chart_config", {})

            if res is not None:
                if isinstance(res, pd.DataFrame) and not res.empty:
                    if viz_type == "bar" and config.get("x") and config.get("y"):
                        import plotly.express as px
                        fig = px.bar(
                            res,
                            x=config["x"],
                            y=config["y"],
                            title=config.get("title", ""),
                            color_discrete_sequence=["#FF6B35"],
                        )
                        fig.update_layout(
                            plot_bgcolor="#1E1E30",
                            paper_bgcolor="#1E1E30",
                            font=dict(color="#F1F5F9"),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    elif viz_type == "scatter" and config.get("x") and config.get("y"):
                        import plotly.express as px
                        fig = px.scatter(
                            res,
                            x=config["x"],
                            y=config["y"],
                            title=config.get("title", ""),
                        )
                        fig.update_layout(
                            plot_bgcolor="#1E1E30",
                            paper_bgcolor="#1E1E30",
                            font=dict(color="#F1F5F9"),
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.dataframe(res, use_container_width=True, hide_index=True)
                elif isinstance(res, (int, float)):
                    st.metric("Result", f"{res:.2f}" if isinstance(res, float) else res)
                elif isinstance(res, pd.DataFrame) and res.empty:
                    st.info("No results matched your query.")
            else:
                st.info("No results to display.")

    # ── API key note ──────────────────────────────────────────────────────
    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.info(
            "Add your ANTHROPIC_API_KEY to .env to enable full natural language queries. "
            "Common queries work without an API key.",
            icon="ℹ️",
        )
