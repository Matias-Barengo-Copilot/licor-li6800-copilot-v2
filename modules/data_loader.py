"""
Data loader: loads attendance from Neon DB.
Work and yearly data use static fallback values until DB tables are added.
"""
import numpy as np
import pandas as pd

from modules.db import get_attendance_df


def load_attendance() -> pd.DataFrame:
    """Load per-student attendance aggregates from Neon DB."""
    return get_attendance_df()


def load_work() -> pd.DataFrame:
    """Work tracking not yet in DB. Returns empty DataFrame with expected schema."""
    return pd.DataFrame(columns=[
        "student_id",
        "% good_num",
        "% needs work_num",
        "% missing_num",
        "Project Team Name",
        "Project Team Role",
        "Portfolio Project - Itch Link",
        "Art v. Programming",
    ])


def load_yearly():
    """Yearly comparison — static fallback until DB tables are defined."""
    enroll_df = pd.DataFrame({
        "Program": [
            "Summer Core", "After-school Core", "Advanced",
            "Studio", "Play Lab", "Senior XP (Summer)",
            "Spring Break Game Design Lab ",
        ],
        "2022_23": [88,  88, 44, 14, np.nan, np.nan, np.nan],
        "2023_24": [96, 103, 58, 20, np.nan, np.nan,   46],
        "2024_25": [96,  99, 90, 29,      8,    22,    51],
    })

    retain_df = pd.DataFrame({
        "Program": [
            "Summer Core", "After-school Core", "Advanced",
            "Studio", "Play Lab", "Senior XP (Summer)",
            "Spring Break Game Design Lab",
        ],
        "2022/23 #":    [61,  49, 38, 14, np.nan, np.nan, np.nan],
        "2022/23 Rate": ["69%", "56%", "86%", "100%", "—", "—", "—"],
        "2023/24 #":    [84,  70, 53, 19, np.nan, np.nan, 33],
        "2023/24 Rate": ["88%", "68%", "91%", "95%", "—", "—", "72%"],
        "2024/25 #":    [89,  68, 74, 28,  7, 18, 37],
        "2024/25 Rate": ["93%", "69%", "82%", "97%", "88%", "82%", "73%"],
    })

    return enroll_df, retain_df


def load_demographics_summary() -> dict:
    """Demographic data — SY2023-24 actuals / 2024-25 projected."""
    ENROLL_2324 = 277
    ENROLL_2425 = 344

    def project(pct_str: str, new_total: int):
        try:
            pct = float(pct_str.strip().rstrip("%")) / 100
        except Exception:
            return None, None
        return round(pct * 100, 1), round(pct * new_total)

    race_src = [
        ("Black or African-American",          "25%", 55),
        ("Hispanic or Latinx",                 "36%", 78),
        ("Asian",                              "29%", 63),
        ("White",                               "9%", 20),
        ("American Indian / Alaska Native",     "1%",  3),
        ("Middle Eastern / North African",      "0%",  0),
        ("Native Hawaiian / Pacific Islander",  "0%",  0),
        ("Prefer not to say",                   "5%", 13),
    ]
    race = []
    for label, pct_str, n_2324 in race_src:
        pct_f, n_2425 = project(pct_str, ENROLL_2425)
        race.append({"category": label, "pct_2324": float(pct_str.rstrip("%")),
                     "n_2324": n_2324, "pct_2425": pct_f, "n_2425": n_2425})

    gender_src = [
        ("Man or Boy",                         "62%", 155),
        ("Woman or Girl",                      "34%",  84),
        ("Non-Binary / Gender Non-Conforming",  "4%",  11),
        ("Another identity",                    "0%",   0),
        ("Prefer not to say",                   "3%",   7),
    ]
    gender = []
    for label, pct_str, n_2324 in gender_src:
        pct_f, n_2425 = project(pct_str, ENROLL_2425)
        gender.append({"category": label, "pct_2324": float(pct_str.rstrip("%")),
                       "n_2324": n_2324, "pct_2425": pct_f, "n_2425": n_2425})

    return {
        "race":   race,
        "gender": gender,
        "disability": [
            {"category": "Has Disability", "pct_2324": 7,  "n_2324": 10,  "pct_2425": 7,  "n_2425": 24},
            {"category": "No / Unknown",   "pct_2324": 93, "n_2324": 132, "pct_2425": 93, "n_2425": 320},
        ],
        "grade": [
            {"category": "9th Grade",  "pct_2324": 35, "n_2324": 97,  "pct_2425": 35, "n_2425": 120},
            {"category": "10th Grade", "pct_2324": 30, "n_2324": 83,  "pct_2425": 30, "n_2425": 103},
            {"category": "11th Grade", "pct_2324": 22, "n_2324": 61,  "pct_2425": 22, "n_2425": 76},
            {"category": "12th Grade", "pct_2324": 13, "n_2324": 36,  "pct_2425": 13, "n_2425": 45},
        ],
        "income": [
            {"category": "< $50,000",           "pct_2324": 42, "n_2324": 116, "pct_2425": 42, "n_2425": 145},
            {"category": "$50,000 – $74,999",   "pct_2324": 25, "n_2324": 69,  "pct_2425": 25, "n_2425": 86},
            {"category": "$75,000 – $99,999",   "pct_2324": 15, "n_2324": 42,  "pct_2425": 15, "n_2425": 52},
            {"category": "$100,000 – $200,000", "pct_2324": 12, "n_2324": 33,  "pct_2425": 12, "n_2425": 41},
            {"category": "> $200,000",          "pct_2324": 6,  "n_2324": 17,  "pct_2425": 6,  "n_2425": 20},
        ],
        "attendance_rates": [
            {"program": "Spring Break Lab",  "rate_2324": 83,   "rate_2425": 85},
            {"program": "Senior XP",         "rate_2324": None, "rate_2425": 88},
            {"program": "Summer Core",       "rate_2324": 94,   "rate_2425": 93},
            {"program": "After-school Core", "rate_2324": 84,   "rate_2425": 82},
            {"program": "Advanced",          "rate_2324": 85,   "rate_2425": 87},
            {"program": "Studio",            "rate_2324": 87,   "rate_2425": 89},
            {"program": "Play Lab",          "rate_2324": None, "rate_2425": 85},
        ],
        "location": [
            {"category": "Brooklyn",     "pct_2324": 38, "n_2425": 131},
            {"category": "Bronx",        "pct_2324": 24, "n_2425": 83},
            {"category": "Queens",       "pct_2324": 20, "n_2425": 69},
            {"category": "Manhattan",    "pct_2324": 14, "n_2425": 48},
            {"category": "Staten Island","pct_2324": 3,  "n_2425": 10},
            {"category": "Non-NYC",      "pct_2324": 1,  "n_2425": 3},
        ],
        "enrollment_2324": ENROLL_2324,
        "enrollment_2425": ENROLL_2425,
        "note": "2024/25 demographic counts projected proportionally from SY2023-24 actuals.",
    }
