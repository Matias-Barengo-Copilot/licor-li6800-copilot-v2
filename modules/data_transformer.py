"""
Data transformation: wide → long format, session attendance, demographics.
"""
import numpy as np
import pandas as pd
import streamlit as st

from modules.data_loader import get_date_columns
from utils.constants import ATTENDANCE_MAP


# Break / holiday markers in the attendance columns
BREAK_MARKERS = {
    "t-giving", "thanksgiving", "winter break", "winter",
    "mid-winter recess", "mid-winter", "eid al-fitr", "eid",
    "spring break", "eid al-adha", "arcade", "n/a",
}


def _is_break_col(col: str) -> bool:
    return col.strip().lower() in BREAK_MARKERS or "-" in col.strip()


@st.cache_data(ttl=3600)
def build_long_attendance(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Convert wide-format attendance to long format.
    One row per (student, session_date).
    """
    date_cols = [c for c in get_date_columns(df_wide) if not _is_break_col(c)]

    id_vars = [
        "student_id", "Preferred Name", "Last Name",
        "Avg_num", "# here", "# late", "# excused", "# afk", "# absent",
    ]

    df_long = df_wide[id_vars + date_cols].melt(
        id_vars=id_vars,
        value_vars=date_cols,
        var_name="raw_date",
        value_name="raw_status",
    )

    # Parse dates
    df_long["session_date"] = pd.to_datetime(
        df_long["raw_date"], format="%m/%d/%y", errors="coerce"
    )

    # Map status codes
    df_long["attendance_status"] = (
        df_long["raw_status"]
        .str.strip()
        .str.lower()
        .map(ATTENDANCE_MAP)
    )

    # Drop rows with no recorded status (future sessions, N/A)
    df_long = df_long[df_long["attendance_status"].notna()].copy()
    df_long = df_long[df_long["session_date"].notna()].copy()

    df_long = df_long.sort_values(["student_id", "session_date"]).reset_index(drop=True)

    return df_long


@st.cache_data(ttl=3600)
def build_weekly_trend(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Compute weekly attendance rates from long-format data.
    """
    df = df_long.copy()
    df["week"] = df["session_date"].dt.to_period("W").dt.start_time

    total_per_week = df.groupby("week")["student_id"].nunique()
    present_per_week = (
        df[df["attendance_status"] == "Present"]
        .groupby("week")["student_id"]
        .nunique()
    )
    late_per_week = (
        df[df["attendance_status"] == "Late"]
        .groupby("week")["student_id"]
        .nunique()
    )

    trend = pd.DataFrame(
        {
            "week": total_per_week.index,
            "total_students": total_per_week.values,
            "present": present_per_week.reindex(total_per_week.index, fill_value=0).values,
            "late": late_per_week.reindex(total_per_week.index, fill_value=0).values,
        }
    )
    trend["attendance_rate"] = (
        (trend["present"] + trend["late"]) / trend["total_students"] * 100
    ).round(1)
    trend["present_only_rate"] = (
        trend["present"] / trend["total_students"] * 100
    ).round(1)

    return trend.sort_values("week").reset_index(drop=True)


@st.cache_data(ttl=3600)
def build_session_trend(df_wide: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-session attendance rates directly from the wide format header row.
    Uses the pre-aggregated totals already in the CSV for accuracy.
    """
    date_cols = [c for c in get_date_columns(df_wide) if not _is_break_col(c)]
    n_students = len(df_wide)

    records = []
    for col in date_cols:
        try:
            session_date = pd.to_datetime(col, format="%m/%d/%y")
        except Exception:
            continue

        # Coerce to string so all-NaN (float) columns are handled safely
        col_data = df_wide[col].fillna("").astype(str).str.strip().str.lower()
        present = (col_data == "p").sum()
        late = (col_data == "l").sum()
        excused = (col_data == "e").sum()
        absent = (col_data == "a").sum()
        afk = (col_data == "afk").sum()
        recorded = present + late + excused + absent + afk
        # Skip future sessions (no one has attended yet)
        if recorded == 0 or session_date > pd.Timestamp.now():
            continue

        records.append(
            {
                "date": session_date,
                "present": present,
                "late": late,
                "excused": excused,
                "absent": absent,
                "afk": afk,
                "recorded": recorded,
                "attendance_rate": round((present + late) / recorded * 100, 1),
            }
        )

    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=3600)
def generate_demographics(student_ids: list) -> pd.DataFrame:
    """Generate synthetic but realistic demographic data for NYC youth arts programs."""
    rng = np.random.default_rng(42)
    n = len(student_ids)

    return pd.DataFrame(
        {
            "student_id": student_ids,
            "gender": rng.choice(
                ["Female", "Male", "Non-binary"],
                size=n,
                p=[0.45, 0.50, 0.05],
            ),
            "race": rng.choice(
                [
                    "Black / African American",
                    "Hispanic / Latino",
                    "Asian",
                    "White",
                    "Multi-racial",
                ],
                size=n,
                p=[0.35, 0.30, 0.15, 0.10, 0.10],
            ),
            "age": rng.integers(14, 19, size=n),
            "site": rng.choice(
                [
                    "Brooklyn Arts Center",
                    "Bronx Creative Hub",
                    "Queens Media Lab",
                    "Manhattan Studio",
                ],
                size=n,
                p=[0.40, 0.25, 0.20, 0.15],
            ),
            "grad_year": rng.choice([2025, 2026, 2027, 2028], size=n),
        }
    )
