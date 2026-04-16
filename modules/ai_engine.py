"""
AI Engine: Claude API integration for insights and natural language queries.
NL queries map to predefined functions only — no exec() or dynamic code.
"""
import json
import os
import re

import numpy as np
import pandas as pd

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


def _get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not ANTHROPIC_AVAILABLE:
        return None
    return anthropic.Anthropic(api_key=api_key)


def _build_data_summary(df_att: pd.DataFrame, df_work: pd.DataFrame) -> dict:
    """Build a compact summary dict to send to Claude."""
    high     = int((df_att["Avg_num"] >= 90).sum())
    low      = int((df_att["Avg_num"] < 70).sum())
    critical = int((df_att["Avg_num"] < 50).sum())
    avg      = float(df_att["Avg_num"].mean()) if not df_att.empty else 0.0
    total    = len(df_att)

    late_flag = int((df_att["# late"] > 5).sum()) if "# late" in df_att.columns else 0

    work_summary = {}
    if len(df_work) > 0 and "% good_num" in df_work.columns and "% missing_num" in df_work.columns:
        good_mean    = df_work["% good_num"].mean()
        missing_mean = df_work["% missing_num"].mean()
        if not (pd.isna(good_mean) or pd.isna(missing_mean)):
            work_summary["avg_good"]    = round(float(good_mean), 1)
            work_summary["avg_missing"] = round(float(missing_mean), 1)
        portfolio_col = "Portfolio Project - Itch Link"
        work_summary["portfolio_done"] = int(
            df_work[portfolio_col].notna().sum() if portfolio_col in df_work.columns else 0
        )

    teams = []
    if "Project Team Name" in df_work.columns:
        teams = df_work["Project Team Name"].dropna().unique().tolist()

    return {
        "total_students":        total,
        "avg_attendance_pct":    round(avg, 1),
        "high_performers_count": high,
        "low_performers_count":  low,
        "critical_count":        critical,
        "late_arrival_concern":  f"{late_flag} students have 5+ late arrivals",
        "work":                  work_summary,
        "teams":                 teams,
        "program":               "3D Game Design – Urban Arts",
        "school_year":           "2025/26",
    }


def generate_insights(df_att: pd.DataFrame, df_work: pd.DataFrame) -> list[str]:
    """
    Call Claude to generate 4 data-driven insights.
    Falls back to rule-based insights if API key not available.
    """
    client  = _get_client()
    summary = _build_data_summary(df_att, df_work)

    if client is None:
        return _fallback_insights(summary)

    prompt = f"""You are an education data analyst for Urban Arts, a NYC youth game design program.
Analyze the following program data and generate exactly 4 bullet-point insights for program staff.

Data:
{json.dumps(summary, indent=2)}

Requirements:
- Be specific with numbers from the data
- Focus on: attendance patterns, at-risk signals, team dynamics, early intervention opportunities
- Keep each bullet under 25 words
- Format: return a JSON array of 4 strings, nothing else

Example format:
["Insight 1 here", "Insight 2 here", "Insight 3 here", "Insight 4 here"]"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw   = response.content[0].text.strip()
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return _fallback_insights(summary)
    except Exception:
        return _fallback_insights(summary)


def _fallback_insights(summary: dict) -> list[str]:
    total    = summary["total_students"]
    high     = summary["high_performers_count"]
    low      = summary["low_performers_count"]
    avg      = summary["avg_attendance_pct"]
    critical = summary["critical_count"]
    late     = summary["late_arrival_concern"]
    work     = summary.get("work", {})
    avg_good    = work.get("avg_good", 0) or 0
    avg_missing = work.get("avg_missing", 0) or 0

    base = round(high / total * 100) if total else 0
    return [
        f"{high} of {total} students ({base}%) have 90%+ attendance — strong engagement core.",
        f"{low} students fall below 70% attendance — immediate outreach recommended.",
        f"{late} — early lateness is a leading indicator of future absenteeism.",
        f"Average work quality is {avg_good}% 'good'; {avg_missing}% of assignments missing.",
    ]


# ── NL Query — predefined functions only, no exec() ──────────────────────────

QUERY_INTENTS = [
    "perfect_attendance",
    "at_risk_students",
    "late_arrivals",
    "missing_assignments",
    "team_performance",
    "attendance_rate",
    "absent_students",
]


def process_nl_query(
    query: str,
    df_att: pd.DataFrame,
    df_work: pd.DataFrame,
) -> dict:
    """
    Map NL query to a predefined query function.
    Uses LLM to classify intent, then executes the matched function.
    No exec() or dynamic SQL.
    """
    client = _get_client()
    if client:
        intent = _classify_intent(client, query)
    else:
        intent = _rule_classify(query)

    return _execute_predefined(intent, query, df_att, df_work)


def _classify_intent(client, query: str) -> str:
    """Ask Claude to classify query into one of QUERY_INTENTS."""
    prompt = (
        f"Classify this education dashboard question into exactly one category.\n"
        f"Question: \"{query}\"\n"
        f"Categories: {', '.join(QUERY_INTENTS)}\n"
        "Return only the category name, nothing else."
    )
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip().lower()
    except Exception:
        return _rule_classify(query)


def _rule_classify(query: str) -> str:
    q = query.lower()
    if "perfect" in q or "100%" in q:
        return "perfect_attendance"
    if "risk" in q or "struggling" in q or "low attendance" in q:
        return "at_risk_students"
    if "late" in q:
        return "late_arrivals"
    if "missing" in q or "assignment" in q:
        return "missing_assignments"
    if "team" in q or "group" in q:
        return "team_performance"
    if "rate" in q or "average" in q or "overall" in q:
        return "attendance_rate"
    if "absent" in q:
        return "absent_students"
    return ""


def _execute_predefined(intent: str, query: str, df_att: pd.DataFrame, df_work: pd.DataFrame) -> dict:
    """Execute the predefined query function for the given intent."""

    if intent == "perfect_attendance":
        result = df_att[df_att["Avg_num"] >= 100][
            ["Preferred Name", "Last Name", "Avg_num", "# here", "# absent"]
        ]
        return {
            "result":      result,
            "viz_type":    "table",
            "explanation": f"{len(result)} students with 100% attendance.",
            "error":       None,
        }

    if intent in ("at_risk_students", "absent_students"):
        result = df_att[df_att["Avg_num"] < 70][
            ["Preferred Name", "Last Name", "Avg_num", "# absent"]
        ].sort_values("Avg_num")
        return {
            "result":      result,
            "viz_type":    "table",
            "explanation": f"{len(result)} students with attendance below 70%.",
            "error":       None,
        }

    if intent == "late_arrivals":
        result = df_att[
            ["Preferred Name", "Last Name", "# late", "# absent", "Avg_num"]
        ].sort_values("# late", ascending=False)
        return {
            "result":      result.head(10),
            "viz_type":    "table",
            "explanation": "Students sorted by number of late arrivals.",
            "error":       None,
        }

    if intent == "missing_assignments":
        if "% missing_num" in df_work.columns and len(df_work) > 0:
            result = df_work[
                ["Preferred Name", "Last Name", "% missing_num", "% good_num"]
            ].sort_values("% missing_num", ascending=False)
            return {
                "result":      result,
                "viz_type":    "table",
                "explanation": "Students sorted by missing assignment percentage.",
                "error":       None,
            }
        return {
            "result":      None,
            "viz_type":    "table",
            "explanation": "Work tracking data not yet available.",
            "error":       None,
        }

    if intent == "team_performance":
        if "Project Team Name" in df_work.columns and "% good_num" in df_work.columns and len(df_work) > 0:
            result = df_work.groupby("Project Team Name")["% good_num"].mean().reset_index()
            result.columns = ["Team", "Avg Work Quality %"]
            return {
                "result":       result,
                "viz_type":     "bar",
                "chart_config": {"x": "Team", "y": "Avg Work Quality %", "title": "Team Work Quality"},
                "explanation":  "Average work quality per project team.",
                "error":        None,
            }
        return {
            "result":      None,
            "viz_type":    "table",
            "explanation": "Team data not yet available.",
            "error":       None,
        }

    if intent == "attendance_rate":
        avg = df_att["Avg_num"].mean() if not df_att.empty else 0
        result = pd.DataFrame([{"Metric": "Average Attendance Rate", "Value": f"{avg:.1f}%"}])
        return {
            "result":      result,
            "viz_type":    "metric",
            "explanation": f"Overall program attendance rate: {avg:.1f}%.",
            "error":       None,
        }

    # Unknown intent
    return {
        "result":      None,
        "viz_type":    "table",
        "explanation": (
            "Try asking: 'perfect attendance', 'at risk students', "
            "'late arrivals', 'missing assignments', 'team performance', or 'attendance rate'."
        ),
        "error": None,
    }
