"""
AI Engine: Claude API integration for insights and natural language queries.
"""
import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st

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
    high = int((df_att["Avg_num"] >= 90).sum())
    low = int((df_att["Avg_num"] < 70).sum())
    critical = int((df_att["Avg_num"] < 50).sum())
    avg = float(df_att["Avg_num"].mean())
    total = len(df_att)

    work_summary = {}
    if "% good_num" in df_work.columns and "% missing_num" in df_work.columns:
        work_summary["avg_good"] = round(float(df_work["% good_num"].mean()), 1)
        work_summary["avg_missing"] = round(float(df_work["% missing_num"].mean()), 1)
        work_summary["portfolio_done"] = int(
            df_work["Portfolio Project - Itch Link"].notna().sum()
            if "Portfolio Project - Itch Link" in df_work.columns else 0
        )

    teams = []
    if "Project Team Name" in df_work.columns:
        teams = df_work["Project Team Name"].dropna().unique().tolist()

    late_flag = int((df_att["# late"] > 5).sum())

    return {
        "total_students": total,
        "avg_attendance_pct": round(avg, 1),
        "high_performers_count": high,
        "low_performers_count": low,
        "critical_count": critical,
        "late_arrival_concern": f"{late_flag} students have 5+ late arrivals",
        "work": work_summary,
        "teams": teams,
        "program": "3D Game Design – Urban Arts",
        "school_year": "2025/26",
    }


@st.cache_data(ttl=14400, show_spinner=False)
def generate_insights(
    _df_att: pd.DataFrame, _df_work: pd.DataFrame
) -> list[str]:
    """
    Call Claude to generate 4 data-driven insights.
    Falls back to rule-based insights if API key not available.
    """
    client = _get_client()
    summary = _build_data_summary(_df_att, _df_work)

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
        raw = response.content[0].text.strip()
        # Extract JSON array from response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return _fallback_insights(summary)
    except Exception:
        return _fallback_insights(summary)


def _fallback_insights(summary: dict) -> list[str]:
    total = summary["total_students"]
    high = summary["high_performers_count"]
    low = summary["low_performers_count"]
    avg = summary["avg_attendance_pct"]
    critical = summary["critical_count"]
    late = summary["late_arrival_concern"]
    work = summary.get("work", {})
    avg_good = work.get("avg_good", 0)
    avg_missing = work.get("avg_missing", 0)
    portfolio = work.get("portfolio_done", 0)

    return [
        f"{high} of {total} students ({round(high/total*100)}%) have 90%+ attendance — strong engagement core.",
        f"{low} students fall below 70% attendance — immediate outreach recommended before further drift.",
        f"{late} — early lateness is a leading indicator of future absenteeism.",
        f"Average work quality is {avg_good}% 'good'; {avg_missing}% of assignments missing — consider structured check-ins.",
    ]


@st.cache_data(ttl=7200, show_spinner=False)
def process_nl_query(
    query: str,
    _df_att: pd.DataFrame,
    _df_work: pd.DataFrame,
) -> dict:
    """
    Process a natural language query against the attendance/work data.
    Returns: {pandas_code, explanation, viz_type, chart_config, error}
    """
    client = _get_client()

    att_cols = list(_df_att.columns[:20])
    work_cols = list(_df_work.columns[:15])

    schema = f"""
DataFrames available:
1. df_att — attendance (wide format)
   Key columns: student_id, 'Preferred Name', 'Last Name', Avg_num (float attendance %),
   '# here', '# late', '# excused', '# afk', '# absent'
   Shape: {_df_att.shape}

2. df_work — work tracking
   Key columns: student_id, '% good_num', '% needs work_num', '% missing_num',
   'Project Team Name', 'Project Team Role', 'Art v. Programming',
   'Portfolio Project - Itch Link', 'Ready to Advance?'
   Shape: {_df_work.shape}
"""

    if client is None:
        return _rule_based_query(query, _df_att, _df_work)

    prompt = f"""You are a data assistant for an education dashboard.
Given a user's natural language question, return a JSON object with safe pandas code to answer it.

Schema:
{schema}

User question: "{query}"

Return ONLY a JSON object (no markdown):
{{
  "pandas_code": "# pandas code here using df_att and df_work; store result in variable named 'result'",
  "viz_type": "table | bar | line | scatter | pie | metric",
  "chart_config": {{"x": "col", "y": "col", "title": "..."}},
  "explanation": "one-sentence answer",
  "error": null
}}

Rules:
- Use only pandas/numpy operations; no eval(), exec(), file I/O, or imports
- 'result' must be a DataFrame or scalar
- Handle missing data with .dropna() or .fillna(0)
- If the question cannot be answered safely, set error to a short message"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return {"error": "Could not parse AI response.", "explanation": ""}
        parsed = json.loads(match.group())
    except Exception as e:
        return {"error": str(e), "explanation": ""}

    # Execute in restricted namespace
    safe_ns = {
        "df_att": _df_att.copy(),
        "df_work": _df_work.copy(),
        "pd": pd,
        "np": np,
    }

    code = parsed.get("pandas_code", "")
    # Safety check: block dangerous patterns
    if any(kw in code for kw in ["exec", "eval", "import", "open(", "__", "os.", "sys."]):
        return {"error": "Query blocked for safety.", "explanation": ""}

    try:
        exec(code, safe_ns)  # noqa: S102
        result = safe_ns.get("result", None)
        parsed["result"] = result
        parsed["error"] = None
    except Exception as e:
        parsed["error"] = f"Execution error: {e}"
        parsed["result"] = None

    return parsed


def _rule_based_query(query: str, df_att: pd.DataFrame, df_work: pd.DataFrame) -> dict:
    """Fallback when no API key: handle common queries with pandas directly."""
    q = query.lower().strip()

    if "perfect" in q or "100%" in q:
        result = df_att[df_att["Avg_num"] >= 100][
            ["Preferred Name", "Last Name", "Avg_num", "# here", "# absent"]
        ]
        return {
            "result": result,
            "viz_type": "table",
            "explanation": f"Found {len(result)} students with 100% attendance.",
            "error": None,
        }

    if "at risk" in q or "risk" in q or "struggling" in q or "low attendance" in q:
        result = df_att[df_att["Avg_num"] < 70][
            ["Preferred Name", "Last Name", "Avg_num", "# absent"]
        ].sort_values("Avg_num")
        return {
            "result": result,
            "viz_type": "table",
            "explanation": f"{len(result)} students with attendance below 70%.",
            "error": None,
        }

    if "team" in q or "group" in q:
        if "Project Team Name" in df_work.columns and "% good_num" in df_work.columns:
            result = df_work.groupby("Project Team Name")["% good_num"].mean().reset_index()
            result.columns = ["Team", "Avg Work Quality %"]
            return {
                "result": result,
                "viz_type": "bar",
                "chart_config": {"x": "Team", "y": "Avg Work Quality %", "title": "Team Work Quality"},
                "explanation": "Average work quality per project team.",
                "error": None,
            }

    if "late" in q:
        result = df_att[["Preferred Name", "Last Name", "# late", "# absent", "Avg_num"]].sort_values(
            "# late", ascending=False
        )
        return {
            "result": result.head(10),
            "viz_type": "table",
            "explanation": "Students sorted by number of late arrivals.",
            "error": None,
        }

    if "missing" in q or "assignment" in q:
        if "% missing_num" in df_work.columns:
            result = df_work[["Preferred Name", "Last Name", "% missing_num", "% good_num"]].sort_values(
                "% missing_num", ascending=False
            )
            return {
                "result": result,
                "viz_type": "table",
                "explanation": "Students sorted by missing assignment percentage.",
                "error": None,
            }

    return {
        "result": None,
        "viz_type": "table",
        "explanation": "Query not recognized without AI. Try: 'perfect attendance', 'at risk students', 'late arrivals', 'missing assignments', or 'team performance'.",
        "error": None,
    }
