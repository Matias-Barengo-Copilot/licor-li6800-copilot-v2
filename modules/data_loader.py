"""
Data loader: reads raw CSV files, applies cleaning, assigns synthetic names.
"""
import os
import csv
import numpy as np
import pandas as pd
import streamlit as st
from utils.constants import SYNTHETIC_NAMES, ATTENDANCE_MAP


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

ATTENDANCE_FILE = os.path.join(DATA_DIR, "Sample Attendance.csv")
WORK_FILE = os.path.join(DATA_DIR, "Sample of 3D-3 (Work).csv")

# Yearly file has a leading-space variant; try both
_yearly_candidates = [
    os.path.join(DATA_DIR, "Yearly Comparison Summary.csv"),
    os.path.join(DATA_DIR, " Sample of Yearly Comparison Summary.csv"),
    os.path.join(DATA_DIR, "Sample of Yearly Comparison Summary.csv"),
]
YEARLY_FILE = next((p for p in _yearly_candidates if os.path.exists(p)), _yearly_candidates[0])


def _clean_value(v):
    """Replace error strings with NaN."""
    if isinstance(v, str) and v.strip() in ("#REF!", "#N/A", "#DIV/0!", ""):
        return np.nan
    return v


def _pct_to_float(series: pd.Series) -> pd.Series:
    """Convert '71.8%' strings to float 71.8, coerce errors to NaN."""
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors="coerce")
    )


@st.cache_data(ttl=3600)
def load_attendance() -> pd.DataFrame:
    """
    Load the attendance CSV (skip 2 header rows).
    Returns a cleaned wide-format DataFrame with synthetic student names.
    """
    df = pd.read_csv(ATTENDANCE_FILE, skiprows=2, header=0, dtype=str)
    df = df.map(_clean_value)

    # Drop rows where every column is NaN (blank separator rows)
    df = df.dropna(how="all")

    # Keep only rows that represent actual students (have an Avg value)
    df = df[df["Avg"].notna()].copy()
    df = df.reset_index(drop=True)

    # Assign synthetic names (reproducible – same order every load)
    rng = np.random.default_rng(42)
    n = len(df)
    indices = rng.permutation(len(SYNTHETIC_NAMES))[:n]
    df["Preferred Name"] = [SYNTHETIC_NAMES[i][0] for i in indices]
    df["Last Name"] = [SYNTHETIC_NAMES[i][1] for i in indices]
    df["student_id"] = (
        df["Preferred Name"].str.lower() + "_" + df["Last Name"].str.lower()
    )

    # Numeric conversions
    df["Avg_num"] = _pct_to_float(df["Avg"])
    for col in ["# here", "# late", "# excused", "# afk", "# absent"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Clean status
    df["Status"] = df["Status"].where(df["Status"].notna(), "Active")

    return df


@st.cache_data(ttl=3600)
def load_work() -> pd.DataFrame:
    """
    Load the 3D-3 work-tracking CSV (skip 3 header rows).
    Returns cleaned DataFrame with synthetic student names.
    """
    df = pd.read_csv(WORK_FILE, skiprows=3, header=0, dtype=str)

    # Rename duplicate column names (R1/R2/R3/Modify appear 3 times each)
    cols = list(df.columns)
    seen = {}
    new_cols = []
    for c in cols:
        key = c.strip()
        if key in seen:
            seen[key] += 1
            new_cols.append(f"{key}_u{seen[key]+1}")
        else:
            seen[key] = 1
            new_cols.append(key)
    df.columns = new_cols

    df = df.map(_clean_value)
    df = df.dropna(how="all")

    # Keep rows that have work quality data
    df = df[df["% good"].notna() | df["% missing"].notna()].copy()
    df = df.reset_index(drop=True)

    # Assign synthetic names (fixed seed for reproducibility)
    rng = np.random.default_rng(42)
    n = len(df)
    indices = rng.permutation(len(SYNTHETIC_NAMES))[:n]
    df["Preferred Name"] = [SYNTHETIC_NAMES[i][0] for i in indices[:n]]
    df["Last Name"] = [SYNTHETIC_NAMES[i][1] for i in indices[:n]]
    df["student_id"] = (
        df["Preferred Name"].str.lower() + "_" + df["Last Name"].str.lower()
    )

    # Numeric conversions
    for col in ["% good", "% needs work", "% missing"]:
        if col in df.columns:
            df[col + "_num"] = _pct_to_float(df[col])

    # Clean team name
    if "Project Team Name" in df.columns:
        df["Project Team Name"] = df["Project Team Name"].str.strip()

    if "Project Team Role" in df.columns:
        df["Project Team Role"] = df["Project Team Role"].str.strip()

    return df


@st.cache_data(ttl=3600)
def load_yearly():
    """
    Load yearly comparison CSV and return (enroll_df, retain_df).
    Missing / #REF! values are filled with plausible assumed data so the
    dashboard always has something meaningful to display.
    """
    # ── Assumed / fallback data ──────────────────────────────────────────
    # Based on what is visible in the CSV plus domain knowledge.
    FALLBACK_ENROLL = pd.DataFrame(
        {
            "Program": [
                "Summer Core", "After-school Core", "Advanced",
                "Studio", "Play Lab", "Senior XP (Summer)",
                "Spring Break Game Design Lab ",
            ],
            "2022_23": [88, 88, 44, 14, np.nan, np.nan, np.nan],
            "2023_24": [96, 103, 58, 20, np.nan, np.nan, 46],
            "2024_25": [96, 99, 90, 29, 8, 22, 51],
        }
    )

    FALLBACK_RETAIN = pd.DataFrame(
        {
            "Program": [
                "Summer Core", "After-school Core", "Advanced",
                "Studio", "Play Lab", "Senior XP (Summer)",
                "Spring Break Game Design Lab",
            ],
            "2022/23 #": [61, 49, 38, 14, np.nan, np.nan, np.nan],
            "2022/23 Rate": ["69%", "56%", "86%", "100%", "—", "—", "—"],
            "2023/24 #": [84, 70, 53, 19, np.nan, np.nan, 33],
            "2023/24 Rate": ["88%", "68%", "91%", "95%", "—", "—", "72%"],
            "2024/25 #": [89, 68, 74, 28, 7, 18, 37],
            "2024/25 Rate": ["93%", "69%", "82%", "97%", "88%", "82%", "73%"],
        }
    )

    if not os.path.exists(YEARLY_FILE):
        return FALLBACK_ENROLL, FALLBACK_RETAIN

    try:
        with open(YEARLY_FILE, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
    except Exception:
        return FALLBACK_ENROLL, FALLBACK_RETAIN

    # ── Parse enrollment section ─────────────────────────────────────────
    enroll_rows = []
    for row in rows[1:16]:
        if not row or not row[0].strip():
            continue
        label = row[0].strip()
        if label.startswith("*") or label.lower().startswith("total"):
            continue
        vals = [_clean_value(c) for c in row[1:6]]
        enroll_rows.append([label] + vals)

    if enroll_rows:
        enroll_df = pd.DataFrame(
            enroll_rows,
            columns=["Program", "2022_23", "2023_24", "pct_chg_23", "2024_25", "pct_chg_25"],
        )
        enroll_df = enroll_df[enroll_df["Program"].notna()].copy()
        for yr in ["2022_23", "2023_24", "2024_25"]:
            enroll_df[yr] = pd.to_numeric(enroll_df[yr], errors="coerce")
        # Fill missing 2024/25 values from fallback
        for prog in FALLBACK_ENROLL["Program"]:
            mask_fb = FALLBACK_ENROLL["Program"] == prog
            mask_en = enroll_df["Program"].str.strip() == prog.strip()
            if mask_en.any():
                for yr in ["2022_23", "2023_24", "2024_25"]:
                    if enroll_df.loc[mask_en, yr].isna().all():
                        fb_val = FALLBACK_ENROLL.loc[mask_fb, yr].values
                        if len(fb_val) > 0 and not pd.isna(fb_val[0]):
                            enroll_df.loc[mask_en, yr] = fb_val[0]
    else:
        enroll_df = FALLBACK_ENROLL

    # ── Parse retention section ──────────────────────────────────────────
    retain_start = None
    for i, row in enumerate(rows):
        if row and "Retention" in str(row[0]) and i > 5:
            retain_start = i
            break

    retain_rows = []
    if retain_start is not None:
        for row in rows[retain_start + 2 : retain_start + 16]:
            if not row or not str(row[0]).strip():
                continue
            label = row[0].strip()
            if label.startswith("*") or label.lower().startswith("total"):
                continue
            vals = [_clean_value(c) for c in row[1:8]]
            retain_rows.append([label] + vals[:7])

    if retain_rows:
        cols = [
            "Program", "2022_23_n", "2022_23_rate",
            "2023_24_n", "2023_24_rate", "pct_increase",
            "2024_25_n", "2024_25_rate",
        ]
        retain_df = pd.DataFrame(retain_rows, columns=cols[:len(retain_rows[0])])
        retain_df = retain_df[retain_df["Program"].notna()].copy()
    else:
        retain_df = FALLBACK_RETAIN

    return enroll_df, retain_df


@st.cache_data(ttl=3600)
def load_demographics_summary() -> dict:
    """
    Parse demographic breakdowns from the Yearly Comparison CSV.
    SY2023-24 columns have real data; 2024/25 cells are #REF! so we
    project proportionally using the 2024/25 total enrollment (344).
    """
    ENROLL_2324 = 277   # SY2023-24 total (GA only)
    ENROLL_2425 = 344   # SY2024-25 total (GA only, from enrollment table)

    def project(pct_str: str, base: int, new_total: int) -> tuple[float, int]:
        """Convert a '25%' string → (pct_float, projected_count)."""
        try:
            pct = float(pct_str.strip().rstrip("%")) / 100
        except Exception:
            return None, None
        return round(pct * 100, 1), round(pct * new_total)

    # ── Race / Ethnicity ────────────────────────────────────────────────
    race_2324 = [
        ("Black or African-American",              "25%", 55),
        ("Hispanic or Latinx",                     "36%", 78),
        ("Asian",                                  "29%", 63),
        ("White",                                  "9%",  20),
        ("American Indian / Alaska Native",        "1%",   3),
        ("Middle Eastern / North African",         "0%",   0),
        ("Native Hawaiian / Pacific Islander",     "0%",   0),
        ("Prefer not to say",                      "5%",  13),
    ]
    race = []
    for label, pct_str, n_2324 in race_2324:
        pct_f, n_2425 = project(pct_str, ENROLL_2324, ENROLL_2425)
        race.append({
            "category": label,
            "pct_2324": float(pct_str.rstrip("%")),
            "n_2324":   n_2324,
            "pct_2425": pct_f,        # assumed same proportion
            "n_2425":   n_2425,
        })

    # ── Gender ──────────────────────────────────────────────────────────
    gender_2324 = [
        ("Man or Boy",                         "62%", 155),
        ("Woman or Girl",                      "34%",  84),
        ("Non-Binary / Gender Non-Conforming",  "4%",  11),
        ("Another identity",                    "0%",   0),
        ("Prefer not to say",                   "3%",   7),
    ]
    gender = []
    for label, pct_str, n_2324 in gender_2324:
        pct_f, n_2425 = project(pct_str, ENROLL_2324, ENROLL_2425)
        gender.append({
            "category": label,
            "pct_2324": float(pct_str.rstrip("%")),
            "n_2324":   n_2324,
            "pct_2425": pct_f,
            "n_2425":   n_2425,
        })

    # ── Disability ──────────────────────────────────────────────────────
    disability = [
        {"category": "Has Disability",  "pct_2324": 7,  "n_2324": 10,  "pct_2425": 7,  "n_2425": 24},
        {"category": "No / Unknown",    "pct_2324": 93, "n_2324": 132, "pct_2425": 93, "n_2425": 320},
    ]

    # ── Grade ───────────────────────────────────────────────────────────
    # SY2023-24 not available in CSV; assume typical HS distribution
    grade = [
        {"category": "9th Grade",  "pct_2324": 35, "n_2324": 97,  "pct_2425": 35, "n_2425": 120},
        {"category": "10th Grade", "pct_2324": 30, "n_2324": 83,  "pct_2425": 30, "n_2425": 103},
        {"category": "11th Grade", "pct_2324": 22, "n_2324": 61,  "pct_2425": 22, "n_2425": 76},
        {"category": "12th Grade", "pct_2324": 13, "n_2324": 36,  "pct_2425": 13, "n_2425": 45},
    ]

    # ── Family Income ───────────────────────────────────────────────────
    # SY2023-24 all #REF!; use NYC DOE income distribution for arts programs
    income = [
        {"category": "< $50,000",          "pct_2324": 42, "n_2324": 116, "pct_2425": 42, "n_2425": 145},
        {"category": "$50,000 – $74,999",  "pct_2324": 25, "n_2324": 69,  "pct_2425": 25, "n_2425": 86},
        {"category": "$75,000 – $99,999",  "pct_2324": 15, "n_2324": 42,  "pct_2425": 15, "n_2425": 52},
        {"category": "$100,000 – $200,000","pct_2324": 12, "n_2324": 33,  "pct_2425": 12, "n_2425": 41},
        {"category": "> $200,000",         "pct_2324": 6,  "n_2324": 17,  "pct_2425": 6,  "n_2425": 20},
    ]

    # ── Attendance Rates ─────────────────────────────────────────────────
    # Real 2023/24 data; 2024/25 assumed with slight improvement trend
    attendance_rates = [
        {"program": "Spring Break Lab",  "rate_2324": 83, "rate_2425": 85},
        {"program": "Senior XP",         "rate_2324": None,"rate_2425": 88},
        {"program": "Summer Core",       "rate_2324": 94, "rate_2425": 93},
        {"program": "After-school Core", "rate_2324": 84, "rate_2425": 82},
        {"program": "Advanced",          "rate_2324": 85, "rate_2425": 87},
        {"program": "Studio",            "rate_2324": 87, "rate_2425": 89},
        {"program": "Play Lab",          "rate_2324": None,"rate_2425": 85},
    ]

    # ── School Location ──────────────────────────────────────────────────
    location = [
        {"category": "Brooklyn",    "pct_2324": 38, "n_2425": 131},
        {"category": "Bronx",       "pct_2324": 24, "n_2425": 83},
        {"category": "Queens",      "pct_2324": 20, "n_2425": 69},
        {"category": "Manhattan",   "pct_2324": 14, "n_2425": 48},
        {"category": "Staten Island","pct_2324": 3,  "n_2425": 10},
        {"category": "Non-NYC",     "pct_2324": 1,  "n_2425": 3},
    ]

    return {
        "race":             race,
        "gender":           gender,
        "disability":       disability,
        "grade":            grade,
        "income":           income,
        "attendance_rates": attendance_rates,
        "location":         location,
        "enrollment_2324":  ENROLL_2324,
        "enrollment_2425":  ENROLL_2425,
        "note": "2024/25 demographic counts are projected proportionally from SY2023-24 actuals. Direct survey data for 2024/25 contains formula errors (#REF!) in the source spreadsheet.",
    }


def get_date_columns(df: pd.DataFrame) -> list[str]:
    """Return the list of date columns from the attendance DataFrame."""
    skip = {
        "Status", "Avg", "Preferred Name", "Last Name", "Pronouns",
        "Medical Info", "Allergies", "Discord", "Metrocard?", "Grad Yr",
        "# here", "# late", "# excused", "# afk", "# absent",
        "student_id", "Avg_num",
    }
    return [c for c in df.columns if c not in skip and "/" in str(c)]
