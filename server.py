"""
Program IQ — FastAPI backend
Serves all analytics data + OpenAI chat.
"""
import json
import os
from typing import AsyncGenerator

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

# ── Import the existing data modules ───────────────────────────────────────
from modules.data_loader import load_attendance, load_work, load_yearly, load_demographics_summary
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

app = FastAPI(title="Program IQ API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Preload all data at startup ─────────────────────────────────────────────
class DataStore:
    att: pd.DataFrame = None
    work: pd.DataFrame = None
    long_att: pd.DataFrame = None
    session: pd.DataFrame = None
    enroll: pd.DataFrame = None
    retain: pd.DataFrame = None
    demographics: pd.DataFrame = None
    perf: pd.DataFrame = None


DS = DataStore()


@app.on_event("startup")
async def startup():
    # Bypass st.cache_data (not running in Streamlit runtime)
    DS.att = load_attendance.__wrapped__()
    DS.work = load_work.__wrapped__()
    DS.enroll, DS.retain = load_yearly.__wrapped__()
    DS.long_att = build_long_attendance.__wrapped__(DS.att)
    DS.session = build_session_trend.__wrapped__(DS.att)
    DS.demographics = generate_demographics.__wrapped__(
        list(DS.att["student_id"].unique())
    )
    DS.perf = student_performance_table(DS.att, DS.work)
    print(f"✅ Data loaded: {len(DS.att)} students, {len(DS.session)} sessions")


def _df_to_records(df: pd.DataFrame) -> list:
    """Convert DataFrame to JSON-safe list of dicts."""
    return json.loads(
        df.replace([np.nan, np.inf, -np.inf], None).to_json(orient="records", date_format="iso")
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/metrics")
def get_metrics():
    metrics = overview_metrics(DS.att, DS.session)
    return metrics


@app.get("/api/session-trend")
def get_session_trend():
    df = DS.session.copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return _df_to_records(df)


@app.get("/api/students")
def get_students(
    min_att: float = 0,
    max_att: float = 100,
    team: str = "All",
    sort: str = "attendance_desc",
):
    df = DS.perf.copy()
    df = df[(df["Attendance %"] >= min_att) & (df["Attendance %"] <= max_att)]
    if team != "All" and "Project Team Name" in df.columns:
        df = df[df["Project Team Name"] == team]

    sort_map = {
        "attendance_desc": ("Attendance %", False),
        "attendance_asc": ("Attendance %", True),
        "absences_desc": ("Absent", False),
        "missing_desc": ("% missing_num", False),
    }
    col, asc = sort_map.get(sort, ("Attendance %", False))
    if col in df.columns:
        df = df.sort_values(col, ascending=asc)

    return _df_to_records(df)


@app.get("/api/teams")
def get_teams():
    teams = team_performance(DS.perf)
    return _df_to_records(teams) if not teams.empty else []


@app.get("/api/at-risk")
def get_at_risk():
    df = at_risk_students(DS.perf)
    return _df_to_records(df) if not df.empty else []


@app.get("/api/attendance-distribution")
def get_att_distribution():
    df = attendance_distribution(DS.att)
    return _df_to_records(df)


@app.get("/api/late-absent-correlation")
def get_late_absent():
    corr_data = late_vs_absent_correlation(DS.att)
    return {
        "corr": corr_data["corr"],
        "data": _df_to_records(corr_data["data"]),
    }


@app.get("/api/yearly-enrollment")
def get_yearly():
    df = yearly_enrollment_trend(DS.enroll)
    if df.empty:
        return []
    return _df_to_records(df)


@app.get("/api/roles")
def get_roles():
    df = role_distribution(DS.work)
    return _df_to_records(df) if not df.empty else []


@app.get("/api/track-preference")
def get_track():
    df = art_vs_programming(DS.work)
    return _df_to_records(df) if not df.empty else []


@app.get("/api/student-sessions/{student_id}")
def get_student_sessions(student_id: str):
    df = DS.long_att[DS.long_att["student_id"] == student_id].copy()
    df["session_date"] = df["session_date"].dt.strftime("%Y-%m-%d")
    return _df_to_records(df[["session_date", "attendance_status"]])


@app.get("/api/teams-list")
def get_teams_list():
    if "Project Team Name" not in DS.perf.columns:
        return []
    teams = DS.perf["Project Team Name"].dropna().unique().tolist()
    return sorted([t for t in teams if t])


# ── OpenAI Chat ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _build_system_prompt() -> str:
    """Build a rich system prompt with live data context."""
    metrics = overview_metrics(DS.att, DS.session)
    teams_df = team_performance(DS.perf)
    at_risk_df = at_risk_students(DS.perf)

    team_summary = ""
    if not teams_df.empty:
        for _, row in teams_df.iterrows():
            team_summary += f"  - {row['Project Team Name']}: {row['Students']} students, {row['Avg_Attendance']:.1f}% attendance, {row['Avg_Good']:.1f}% work quality\n"

    at_risk_names = ""
    if not at_risk_df.empty:
        for _, row in at_risk_df.head(8).iterrows():
            at_risk_names += f"  - {row['First Name']} {row['Last Name']}: {row['Attendance %']:.1f}% attendance, Priority={row['Priority']}\n"

    return f"""You are an expert education data analyst assistant for Urban Arts, a NYC youth game design program.
You have access to real program data for the 2025/26 school year.

LIVE DATA SUMMARY:
- Program: 3D Game Design, Urban Arts NYC
- Total students: {metrics['total_students']}
- Average attendance: {metrics['avg_attendance']:.1f}%
- Sessions recorded: {metrics['sessions']}
- High performers (≥90% attendance): {metrics['high_performers']}
- Students needing attention (<70%): {metrics['low_performers']}
- Critical (<50% attendance): {metrics['critical_students']}

PROJECT TEAMS:
{team_summary or '  (no team data)'}

AT-RISK STUDENTS:
{at_risk_names or '  (none flagged)'}

STUDENT DEMOGRAPHICS (SY2023-24 actuals / 2024-25 projected):
- Race: 36% Hispanic/Latinx, 29% Asian, 25% Black/African-American, 9% White
- Gender: 62% Man/Boy, 34% Woman/Girl, 4% Non-Binary
- 7% of students have a documented disability
- Income: 42% from households earning <$50k/yr; 67% from households <$75k/yr
- Locations: 38% Brooklyn, 24% Bronx, 20% Queens, 14% Manhattan
- Grades: 35% 9th, 30% 10th, 22% 11th, 13% 12th

PROGRAM HISTORY (2024/25):
- 668 total students across all programs
- 3D Game Dev grew 55% year-over-year
- Summer Core: 93% retention rate (best program)
- Studio: 97% retention
- After-school Core: 69% retention (needs focus)

Your role:
- Answer questions about attendance patterns, student performance, and program trends
- Provide actionable insights for program staff (not just statistics)
- Flag specific at-risk students when asked
- Suggest interventions based on data patterns
- Be concise, specific, and use actual numbers from the data above

Keep responses focused and under 250 words unless asked for detail."""


# ── Tool definition for chart rendering ────────────────────────────────────
CHART_TOOL = {
    "type": "function",
    "function": {
        "name": "show_chart",
        "description": (
            "Display a visual chart or graph directly in the chat. "
            "Use this whenever the user asks for a graph, chart, or visualization, "
            "or when displaying data visually would be clearer than listing numbers. "
            "Always prefer a chart over a text list when showing distributions or comparisons."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["pie", "donut", "bar", "horizontal_bar", "line"],
                    "description": "Chart type. Use pie/donut for distributions, bar for comparisons, line for trends.",
                },
                "title": {"type": "string", "description": "Descriptive chart title"},
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "value": {"type": "number"},
                        },
                        "required": ["label", "value"],
                    },
                    "description": "Array of {label, value} data points",
                },
                "unit": {
                    "type": "string",
                    "description": "Unit for values, e.g. '%', 'students', 'sessions'",
                    "default": "%",
                },
                "insight": {
                    "type": "string",
                    "description": "One-sentence key takeaway to display below the chart",
                },
            },
            "required": ["chart_type", "title", "data"],
        },
    },
}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
    except ImportError:
        raise HTTPException(status_code=500, detail="openai package not installed")

    system_prompt = _build_system_prompt()
    messages = [{"role": "system", "content": system_prompt}]
    for msg in req.messages:
        messages.append({"role": msg.role, "content": msg.content})

    async def stream_response() -> AsyncGenerator[str, None]:
        try:
            stream = await client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=[CHART_TOOL],
                tool_choice="auto",
                max_tokens=800,
                temperature=0.3,
                stream=True,
            )

            # Accumulate tool call arguments across streaming chunks
            tool_calls_acc: dict[int, dict] = {}
            finish_reason = None

            async for chunk in stream:
                choice = chunk.choices[0]
                finish_reason = choice.finish_reason

                # Stream plain text content immediately
                if choice.delta.content:
                    yield f"data: {json.dumps({'content': choice.delta.content})}\n\n"

                # Accumulate tool call argument fragments
                if choice.delta.tool_calls:
                    for tc in choice.delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": tc.id or "",
                                "name": tc.function.name if tc.function else "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc.function.arguments

            # Process completed tool calls after stream ends
            if finish_reason == "tool_calls" and tool_calls_acc:
                for tc in tool_calls_acc.values():
                    if tc["name"] == "show_chart":
                        try:
                            args = json.loads(tc["arguments"])
                            yield f"data: {json.dumps({'type': 'chart', 'chart': args})}\n\n"

                            # Follow-up: let model add a text comment after the chart
                            followup_messages = messages + [
                                {
                                    "role": "assistant",
                                    "tool_calls": [{
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {"name": "show_chart", "arguments": tc["arguments"]},
                                    }],
                                },
                                {
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": "Chart rendered successfully.",
                                },
                            ]
                            followup = await client.chat.completions.create(
                                model="gpt-4o",
                                messages=followup_messages,
                                max_tokens=200,
                                temperature=0.3,
                            )
                            comment = followup.choices[0].message.content
                            if comment:
                                yield f"data: {json.dumps({'content': comment})}\n\n"
                        except json.JSONDecodeError:
                            pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/demographics")
def get_demographics():
    return load_demographics_summary.__wrapped__()


# ── Programs endpoints ───────────────────────────────────────────────────────

PROGRAMS = [
    {
        "id": "summer_core",
        "name": "Summer Core",
        "subtitle": "2D Game Dev",
        "type": "Summer",
        "icon": "☀️",
        "color": "#f59e0b",
        "enrolled_2324": 96, "completed_2324": 89, "retention_2324": 93,
        "enrolled_2425": 104, "completed_2425": None, "retention_2425": None,
        "description": "Flagship summer program introducing game design fundamentals.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 36},
            {"label": "Asian", "value": 29},
            {"label": "Black/African-Am.", "value": 25},
            {"label": "White", "value": 9},
            {"label": "Other", "value": 1},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 62},
            {"label": "Woman/Girl", "value": 34},
            {"label": "Non-Binary", "value": 4},
        ],
        "trend_baseline": 93,
        "live": False,
    },
    {
        "id": "afterschool_core",
        "name": "After-school Core",
        "subtitle": "2D Game Dev",
        "type": "After-school",
        "icon": "🏫",
        "color": "#ef4444",
        "enrolled_2324": 99, "completed_2324": 68, "retention_2324": 69,
        "enrolled_2425": 105, "completed_2425": None, "retention_2425": None,
        "description": "After-school game design track with highest enrollment.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 38},
            {"label": "Asian", "value": 27},
            {"label": "Black/African-Am.", "value": 27},
            {"label": "White", "value": 7},
            {"label": "Other", "value": 1},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 65},
            {"label": "Woman/Girl", "value": 31},
            {"label": "Non-Binary", "value": 4},
        ],
        "trend_baseline": 69,
        "live": False,
    },
    {
        "id": "3d_game_dev",
        "name": "3D Game Dev",
        "subtitle": "Current Program",
        "type": "After-school",
        "icon": "🎮",
        "color": "#ff6b35",
        "enrolled_2324": 90, "completed_2324": 74, "retention_2324": 82,
        "enrolled_2425": 140, "completed_2425": None, "retention_2425": None,
        "description": "Advanced 3D game development — grew 55% year-over-year.",
        "race": None,   # use live demographics
        "gender": None,
        "trend_baseline": None,  # use live session data
        "live": True,
    },
    {
        "id": "studio",
        "name": "Studio",
        "subtitle": "Advanced Track",
        "type": "After-school",
        "icon": "🎨",
        "color": "#7c3aed",
        "enrolled_2324": 29, "completed_2324": 28, "retention_2324": 97,
        "enrolled_2425": 32, "completed_2425": None, "retention_2425": None,
        "description": "Selective advanced studio for returning students.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 34},
            {"label": "Asian", "value": 31},
            {"label": "Black/African-Am.", "value": 24},
            {"label": "White", "value": 10},
            {"label": "Other", "value": 1},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 58},
            {"label": "Woman/Girl", "value": 37},
            {"label": "Non-Binary", "value": 5},
        ],
        "trend_baseline": 97,
        "live": False,
    },
    {
        "id": "play_lab",
        "name": "Play Lab",
        "subtitle": "Exploratory Track",
        "type": "After-school",
        "icon": "🧪",
        "color": "#10b981",
        "enrolled_2324": 8, "completed_2324": 7, "retention_2324": 88,
        "enrolled_2425": 10, "completed_2425": None, "retention_2425": None,
        "description": "Small-cohort experimental game design exploration.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 40},
            {"label": "Asian", "value": 25},
            {"label": "Black/African-Am.", "value": 25},
            {"label": "White", "value": 10},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 60},
            {"label": "Woman/Girl", "value": 40},
        ],
        "trend_baseline": 88,
        "live": False,
    },
    {
        "id": "senior_xp",
        "name": "Senior XP",
        "subtitle": "Alumni Track",
        "type": "Summer",
        "icon": "🏆",
        "color": "#3b82f6",
        "enrolled_2324": 22, "completed_2324": 18, "retention_2324": 82,
        "enrolled_2425": 24, "completed_2425": None, "retention_2425": None,
        "description": "Capstone experience for graduating senior students.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 36},
            {"label": "Asian", "value": 28},
            {"label": "Black/African-Am.", "value": 27},
            {"label": "White", "value": 9},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 55},
            {"label": "Woman/Girl", "value": 41},
            {"label": "Non-Binary", "value": 4},
        ],
        "trend_baseline": 82,
        "live": False,
    },
    {
        "id": "spring_break",
        "name": "Spring Break Lab",
        "subtitle": "Intensive",
        "type": "Special",
        "icon": "🌱",
        "color": "#06b6d4",
        "enrolled_2324": 51, "completed_2324": 37, "retention_2324": 73,
        "enrolled_2425": 55, "completed_2425": None, "retention_2425": None,
        "description": "Intensive one-week Spring Break game design sprint.",
        "race": [
            {"label": "Hispanic/Latinx", "value": 37},
            {"label": "Asian", "value": 28},
            {"label": "Black/African-Am.", "value": 26},
            {"label": "White", "value": 9},
        ],
        "gender": [
            {"label": "Man/Boy", "value": 63},
            {"label": "Woman/Girl", "value": 33},
            {"label": "Non-Binary", "value": 4},
        ],
        "trend_baseline": 73,
        "live": False,
    },
]


def _synthetic_trend(baseline: int, n_sessions: int = 18) -> list:
    """Generate a plausible session attendance trend from a retention baseline."""
    import random
    rng = random.Random(baseline)
    trend = []
    # Start slightly below baseline, fluctuate ±8 pts
    current = baseline - 5
    for i in range(n_sessions):
        delta = rng.randint(-6, 8)
        current = max(50, min(100, current + delta))
        trend.append({"session": i + 1, "rate": round(current, 1)})
    return trend


@app.get("/api/programs")
def get_programs():
    """List all programs with summary stats."""
    result = []
    for p in PROGRAMS:
        result.append({
            "id": p["id"],
            "name": p["name"],
            "subtitle": p["subtitle"],
            "type": p["type"],
            "icon": p["icon"],
            "color": p["color"],
            "description": p["description"],
            "enrolled_2324": p["enrolled_2324"],
            "completed_2324": p["completed_2324"],
            "retention_2324": p["retention_2324"],
            "enrolled_2425": p["enrolled_2425"],
            "live": p["live"],
        })
    return result


@app.get("/api/program/{program_id}")
def get_program_detail(program_id: str):
    """Return detailed drill-down data for a specific program."""
    prog = next((p for p in PROGRAMS if p["id"] == program_id), None)
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    # Attendance trend
    if prog["live"] and DS.session is not None:
        df = DS.session.copy()
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        trend = [
            {"session": i + 1, "date": row.date, "rate": round(float(row.attendance_rate), 1)}
            for i, row in enumerate(df.itertuples())
        ]
        # Live metrics
        live_metrics = {
            "total_students": int(len(DS.att)),
            "avg_attendance": float(DS.perf["Attendance %"].mean()) if DS.perf is not None else None,
            "at_risk": int((DS.perf["Attendance %"] < 70).sum()) if DS.perf is not None else 0,
        }
        # Live demographics from actual students
        demo = load_demographics_summary.__wrapped__()
        race = [{"label": r["category"], "value": r["pct_2425"]} for r in demo.get("race", []) if r.get("pct_2425", 0) > 0]
        gender = [{"label": g["category"], "value": g["pct_2425"]} for g in demo.get("gender", []) if g.get("pct_2425", 0) > 0]
    else:
        trend = _synthetic_trend(prog["trend_baseline"])
        live_metrics = None
        race = prog["race"] or []
        gender = prog["gender"] or []

    return {
        "id": prog["id"],
        "name": prog["name"],
        "subtitle": prog["subtitle"],
        "type": prog["type"],
        "icon": prog["icon"],
        "color": prog["color"],
        "description": prog["description"],
        "enrolled_2324": prog["enrolled_2324"],
        "completed_2324": prog["completed_2324"],
        "retention_2324": prog["retention_2324"],
        "enrolled_2425": prog["enrolled_2425"],
        "live": prog["live"],
        "live_metrics": live_metrics,
        "trend": trend,
        "race": race,
        "gender": gender,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "students": len(DS.att) if DS.att is not None else 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
