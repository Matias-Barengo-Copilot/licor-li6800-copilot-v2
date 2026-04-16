"""
Data transformation utilities.
Long-format and session-trend data now come from DB via modules/db.py.
generate_demographics() and build_weekly_trend() remain here.
"""
import numpy as np
import pandas as pd


def build_weekly_trend(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Compute weekly attendance rates from long-format attendance data.
    Expects columns: student_id, session_date, attendance_status.
    """
    df = df_long.copy()
    df["week"] = df["session_date"].dt.to_period("W").dt.start_time

    total_per_week   = df.groupby("week")["student_id"].nunique()
    present_per_week = (
        df[df["attendance_status"] == "Present"].groupby("week")["student_id"].nunique()
    )

    trend = pd.DataFrame({
        "week":           total_per_week.index,
        "total_students": total_per_week.values,
        "present":        present_per_week.reindex(total_per_week.index, fill_value=0).values,
    })
    trend["attendance_rate"] = (
        trend["present"] / trend["total_students"] * 100
    ).round(1)

    return trend.sort_values("week").reset_index(drop=True)


def generate_demographics(student_ids: list) -> pd.DataFrame:
    """Generate synthetic demographic data for a list of student IDs."""
    rng = np.random.default_rng(42)
    n   = len(student_ids)

    return pd.DataFrame({
        "student_id": student_ids,
        "gender": rng.choice(
            ["Female", "Male", "Non-binary"], size=n, p=[0.45, 0.50, 0.05]
        ),
        "race": rng.choice(
            ["Black / African American", "Hispanic / Latino", "Asian", "White", "Multi-racial"],
            size=n, p=[0.35, 0.30, 0.15, 0.10, 0.10],
        ),
        "age":       rng.integers(14, 19, size=n),
        "site": rng.choice(
            ["Brooklyn Arts Center", "Bronx Creative Hub", "Queens Media Lab", "Manhattan Studio"],
            size=n, p=[0.40, 0.25, 0.20, 0.15],
        ),
        "grad_year": rng.choice([2025, 2026, 2027, 2028], size=n),
    })
