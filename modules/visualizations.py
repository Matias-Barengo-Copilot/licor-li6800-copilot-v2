"""
Visualization factory: all Plotly charts used across pages.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.constants import CHART_THEME, COLORS, ATTENDANCE_COLORS


def _apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        font=CHART_THEME["font"],
        title=dict(text=title, font=dict(size=16, color=COLORS["text"])),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            bgcolor=COLORS["surface_light"],
            bordercolor=COLORS["border"],
            borderwidth=1,
        ),
    )
    fig.update_xaxes(gridcolor=CHART_THEME["gridcolor"], zerolinecolor=CHART_THEME["gridcolor"])
    fig.update_yaxes(gridcolor=CHART_THEME["gridcolor"], zerolinecolor=CHART_THEME["gridcolor"])
    return fig


def session_attendance_chart(df_session: pd.DataFrame) -> go.Figure:
    """Line chart of attendance rate per session over the school year."""
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_session["date"],
            y=df_session["attendance_rate"],
            mode="lines+markers",
            name="Attendance Rate",
            line=dict(color=COLORS["primary"], width=2.5),
            marker=dict(size=6, color=COLORS["primary"]),
            fill="tozeroy",
            fillcolor="rgba(255,107,53,0.15)",
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Attendance: %{y:.1f}%<extra></extra>",
        )
    )

    # Add 80% target line
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=COLORS["warning"],
        annotation_text="80% target",
        annotation_position="top right",
        annotation_font_color=COLORS["warning"],
    )

    fig.update_layout(
        xaxis_title="Session Date",
        yaxis_title="Attendance Rate (%)",
        yaxis_range=[0, 105],
        hovermode="x unified",
    )

    return _apply_theme(fig, "Class Attendance Rate – School Year 2025/26")


def attendance_distribution_chart(df_dist: pd.DataFrame) -> go.Figure:
    """Bar chart of student count per attendance band."""
    color_map = {
        "<60%": COLORS["danger"],
        "60–70%": "#F97316",
        "70–80%": COLORS["warning"],
        "80–90%": "#84CC16",
        "90–100%": COLORS["success"],
    }
    colors = [color_map.get(b, COLORS["primary"]) for b in df_dist["Attendance Band"]]

    fig = go.Figure(
        go.Bar(
            x=df_dist["Attendance Band"],
            y=df_dist["Students"],
            marker_color=colors,
            text=df_dist["Students"],
            textposition="outside",
            textfont=dict(color=COLORS["text"]),
            hovertemplate="<b>%{x}</b><br>%{y} students<extra></extra>",
        )
    )
    fig.update_layout(yaxis_title="Number of Students", xaxis_title="Attendance Band")
    return _apply_theme(fig, "Students by Attendance Rate")


def team_performance_chart(df_teams: pd.DataFrame) -> go.Figure:
    """Grouped bar chart comparing teams on attendance and work quality."""
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Avg Attendance %",
            x=df_teams["Project Team Name"],
            y=df_teams["Avg_Attendance"],
            marker_color=COLORS["primary"],
            text=df_teams["Avg_Attendance"].round(1).astype(str) + "%",
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Avg Work Quality %",
            x=df_teams["Project Team Name"],
            y=df_teams["Avg_Good"],
            marker_color=COLORS["accent"],
            text=df_teams["Avg_Good"].round(1).astype(str) + "%",
            textposition="outside",
        )
    )

    fig.update_layout(
        barmode="group",
        yaxis_title="Percentage (%)",
        yaxis_range=[0, 115],
        xaxis_title="Project Team",
    )
    return _apply_theme(fig, "Team Performance: Attendance vs Work Quality")


def late_absent_scatter(corr_data: dict) -> go.Figure:
    """Scatter plot of late arrivals vs absences with trendline."""
    df = corr_data["data"]
    corr = corr_data["corr"]

    fig = px.scatter(
        df,
        x="# late",
        y="# absent",
        color="Avg_num",
        hover_name="Name",
        color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
        range_color=[40, 100],
        labels={
            "# late": "Number of Late Arrivals",
            "# absent": "Number of Absences",
            "Avg_num": "Attendance %",
        },
    )

    # Trendline
    if corr is not None and len(df) >= 3:
        import numpy as np
        z = np.polyfit(df["# late"], df["# absent"], 1)
        p = np.poly1d(z)
        x_range = range(int(df["# late"].min()), int(df["# late"].max()) + 1)
        fig.add_trace(
            go.Scatter(
                x=list(x_range),
                y=[p(x) for x in x_range],
                mode="lines",
                name=f"Trend (r={corr})",
                line=dict(color=COLORS["warning"], dash="dash", width=2),
            )
        )

    fig.update_layout(
        coloraxis_colorbar=dict(
            title="Attendance %",
            tickfont=dict(color=COLORS["text"]),
            titlefont=dict(color=COLORS["text"]),
        )
    )

    title = f"Late Arrivals vs Absences"
    if corr is not None:
        title += f"  (correlation r={corr})"
    return _apply_theme(fig, title)


def role_distribution_chart(df_roles: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of role distribution."""
    fig = go.Figure(
        go.Bar(
            y=df_roles["Role"],
            x=df_roles["Count"],
            orientation="h",
            marker_color=COLORS["accent"],
            text=df_roles["Count"],
            textposition="outside",
        )
    )
    fig.update_layout(xaxis_title="Students", yaxis_title="Role")
    return _apply_theme(fig, "Team Role Distribution")


def art_vs_programming_chart(df: pd.DataFrame) -> go.Figure:
    """Pie chart of Art vs Programming track preference."""
    fig = go.Figure(
        go.Pie(
            labels=df["Track"],
            values=df["Count"],
            hole=0.45,
            marker_colors=[COLORS["primary"], COLORS["accent"], COLORS["success"]],
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value} students (%{percent})<extra></extra>",
        )
    )
    return _apply_theme(fig, "Art vs Programming Track Preference")


def yearly_enrollment_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart for multi-year enrollment trends."""
    fig = px.line(
        df,
        x="Year",
        y="Enrolled",
        color="Program",
        markers=True,
        color_discrete_sequence=CHART_THEME["colorway"],
        labels={"Enrolled": "Students Enrolled", "Year": "Academic Year"},
    )
    fig.update_traces(line_width=2.5, marker_size=8)
    return _apply_theme(fig, "Program Enrollment Trends (2022–2025)")


def status_donut(df_session: pd.DataFrame) -> go.Figure:
    """Donut chart of most recent session's status breakdown."""
    if df_session.empty:
        return go.Figure()
    last = df_session.iloc[-1]
    labels = ["Present", "Late", "Excused", "Absent", "AFK"]
    values = [
        last.get("present", 0),
        last.get("late", 0),
        last.get("excused", 0),
        last.get("absent", 0),
        last.get("afk", 0),
    ]
    colors = [
        COLORS["success"], COLORS["warning"], "#3B82F6",
        COLORS["danger"], COLORS["accent"],
    ]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker_colors=colors,
            textinfo="label+value",
            hovertemplate="<b>%{label}</b>: %{value} students<extra></extra>",
        )
    )
    return _apply_theme(fig, f"Last Session ({last['date'].strftime('%b %d')})")


def student_sparkline(df_long: pd.DataFrame, student_id: str) -> go.Figure:
    """Mini sparkline of a single student's attendance over time."""
    df = df_long[df_long["student_id"] == student_id].sort_values("session_date")
    df = df.copy()
    df["present_val"] = df["attendance_status"].map(
        {"Present": 1, "Late": 0.5, "Excused": 0.5, "Absent": 0, "Away (AFK)": 0.5}
    )

    colors = df["attendance_status"].map(
        {
            "Present": COLORS["success"],
            "Late": COLORS["warning"],
            "Excused": "#3B82F6",
            "Absent": COLORS["danger"],
            "Away (AFK)": COLORS["accent"],
        }
    ).tolist()

    fig = go.Figure(
        go.Bar(
            x=df["session_date"],
            y=df["present_val"],
            marker_color=colors,
            hovertemplate="<b>%{x|%b %d}</b><br>%{customdata}<extra></extra>",
            customdata=df["attendance_status"],
        )
    )
    fig.update_layout(
        height=120,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        yaxis=dict(range=[0, 1.2], visible=False),
        xaxis=dict(visible=False),
    )
    fig.update_layout(
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
    )
    return fig
