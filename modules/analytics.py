"""
Analytics: compute all key metrics from cleaned data.
"""
import numpy as np
import pandas as pd
from utils.constants import AT_RISK_THRESHOLDS


def overview_metrics(df_attendance: pd.DataFrame, df_session: pd.DataFrame) -> dict:
    """Return top-level KPIs for the overview page."""
    total = len(df_attendance)
    avg_att = df_attendance["Avg_num"].mean()
    sessions = len(df_session)

    # Students above/below thresholds
    high = (df_attendance["Avg_num"] >= 90).sum()
    low = (df_attendance["Avg_num"] < AT_RISK_THRESHOLDS["attendance_low"]).sum()
    critical = (df_attendance["Avg_num"] < AT_RISK_THRESHOLDS["attendance_critical"]).sum()

    # Most recent session with non-zero attendance
    non_zero = df_session[df_session["attendance_rate"] > 0]
    recent_rate = float(non_zero["attendance_rate"].iloc[-1]) if len(non_zero) > 0 else 0.0

    # Delta vs. session before that
    delta = 0.0
    if len(non_zero) >= 2:
        delta = float(non_zero["attendance_rate"].iloc[-1] - non_zero["attendance_rate"].iloc[-2])

    return {
        "total_students": total,
        "avg_attendance": round(avg_att, 1),
        "sessions": sessions,
        "high_performers": int(high),
        "low_performers": int(low),
        "critical_students": int(critical),
        "recent_session_rate": round(recent_rate, 1),
        "recent_delta": round(delta, 1),
    }


def student_performance_table(df_att: pd.DataFrame, df_work: pd.DataFrame) -> pd.DataFrame:
    """
    Merge attendance and work data into a single student performance table.
    """
    # Attendance side
    att = df_att[
        ["student_id", "Preferred Name", "Last Name", "Avg_num",
         "# here", "# late", "# excused", "# afk", "# absent"]
    ].copy()
    att.columns = [
        "student_id", "First Name", "Last Name", "Attendance %",
        "Present", "Late", "Excused", "AFK", "Absent"
    ]

    # Work side
    work_cols = ["student_id", "% good_num", "% needs work_num", "% missing_num",
                 "Project Team Name", "Project Team Role", "Portfolio Project - Itch Link",
                 "Art v. Programming"]
    existing = [c for c in work_cols if c in df_work.columns]
    work = df_work[existing].copy()

    merged = att.merge(work, on="student_id", how="left")

    # At-risk flag
    merged["At Risk"] = (
        (merged["Attendance %"] < AT_RISK_THRESHOLDS["attendance_low"]) |
        (merged["% missing_num"] > AT_RISK_THRESHOLDS["missing_work_high"]) |
        (merged["Absent"] > AT_RISK_THRESHOLDS["absences_high"])
    )

    merged["Priority"] = merged.apply(_priority, axis=1)

    return merged.sort_values("Attendance %", ascending=False).reset_index(drop=True)


def _priority(row) -> str:
    att = row.get("Attendance %", 100)
    missing = row.get("% missing_num", 0) or 0
    absent = row.get("Absent", 0) or 0
    if att < AT_RISK_THRESHOLDS["attendance_critical"] or missing > 70:
        return "HIGH"
    if att < AT_RISK_THRESHOLDS["attendance_low"] or missing > AT_RISK_THRESHOLDS["missing_work_high"] or absent > AT_RISK_THRESHOLDS["absences_high"]:
        return "MEDIUM"
    return "OK"


def at_risk_students(df_perf: pd.DataFrame) -> pd.DataFrame:
    """Return only at-risk students, sorted by priority."""
    at_risk = df_perf[df_perf["At Risk"]].copy()
    priority_order = {"HIGH": 0, "MEDIUM": 1, "OK": 2}
    at_risk["_sort"] = at_risk["Priority"].map(priority_order)
    return at_risk.sort_values(["_sort", "Attendance %"]).drop("_sort", axis=1)


def team_performance(df_perf: pd.DataFrame) -> pd.DataFrame:
    """Aggregate metrics by project team."""
    if "Project Team Name" not in df_perf.columns:
        return pd.DataFrame()

    df = df_perf[df_perf["Project Team Name"].notna()].copy()

    agg = df.groupby("Project Team Name").agg(
        Students=("student_id", "count"),
        Avg_Attendance=("Attendance %", "mean"),
        Avg_Good=("% good_num", "mean"),
        Avg_Missing=("% missing_num", "mean"),
        Total_Absences=("Absent", "sum"),
    ).reset_index()

    agg["Avg_Attendance"] = agg["Avg_Attendance"].round(1)
    agg["Avg_Good"] = agg["Avg_Good"].round(1)
    agg["Avg_Missing"] = agg["Avg_Missing"].round(1)

    return agg.sort_values("Avg_Attendance", ascending=False).reset_index(drop=True)


def attendance_distribution(df_att: pd.DataFrame) -> pd.DataFrame:
    """Bin students by attendance percentage band."""
    bins = [0, 60, 70, 80, 90, 101]
    labels = ["<60%", "60–70%", "70–80%", "80–90%", "90–100%"]
    df_att = df_att.copy()
    df_att["band"] = pd.cut(df_att["Avg_num"], bins=bins, labels=labels, right=False)
    counts = df_att["band"].value_counts().sort_index().reset_index()
    counts.columns = ["Attendance Band", "Students"]
    return counts


def late_vs_absent_correlation(df_att: pd.DataFrame) -> dict:
    """Return correlation coefficient and scatter data for late vs absent."""
    df = df_att[["# late", "# absent", "Preferred Name", "Last Name", "Avg_num"]].dropna()
    df = df.copy()
    df["Name"] = df["Preferred Name"] + " " + df["Last Name"]
    if len(df) < 3:
        return {"corr": None, "data": df}
    corr = df["# late"].corr(df["# absent"])
    return {"corr": round(corr, 3), "data": df}


def yearly_enrollment_trend(enroll_df: pd.DataFrame) -> pd.DataFrame:
    """Reshape yearly enrollment for a line/bar chart."""
    programs = [
        "Summer Core", "After-school Core", "Advanced", "Studio", "Play Lab",
        "Senior XP (Summer)", "Spring Break Game Design Lab ",
    ]
    df = enroll_df[enroll_df["Program"].isin(programs)].copy()
    melted = df.melt(
        id_vars=["Program"],
        value_vars=["2022_23", "2023_24", "2024_25"],
        var_name="Year",
        value_name="Enrolled",
    )
    melted["Year"] = melted["Year"].str.replace("_", "/")
    melted = melted.dropna(subset=["Enrolled"])
    return melted


def role_distribution(df_work: pd.DataFrame) -> pd.DataFrame:
    """Count students by project team role."""
    if "Project Team Role" not in df_work.columns:
        return pd.DataFrame()
    roles = df_work["Project Team Role"].dropna().str.strip()
    counts = roles.value_counts().reset_index()
    counts.columns = ["Role", "Count"]
    return counts


def art_vs_programming(df_work: pd.DataFrame) -> pd.DataFrame:
    """Count students by track preference."""
    if "Art v. Programming" not in df_work.columns:
        return pd.DataFrame()
    track = df_work["Art v. Programming"].dropna().str.strip()
    counts = track.value_counts().reset_index()
    counts.columns = ["Track", "Count"]
    return counts
