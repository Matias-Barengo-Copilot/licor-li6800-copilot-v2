"""
Program IQ — FastAPI backend
Serves all analytics data + OpenAI chat.
Data sourced from shared Neon DB (read-only).
"""
import json
import os
from typing import AsyncGenerator

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

load_dotenv()

import bcrypt as _bcrypt
from datetime import datetime, timedelta, timezone

import jwt as pyjwt

from modules.db import (
    get_attendance_df, get_session_trend_df, get_attendance_long_df, get_user_by_email,
    get_programs, get_program_by_id, get_session_trend_for_program,
    get_program_attendance_rates, get_at_risk_for_program,
)
from modules.data_loader import load_work, load_yearly, load_demographics_summary
from modules.data_transformer import generate_demographics
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

JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is required. Set it in your .env before starting Program IQ."
    )

# ── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001",
                   "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── JWT middleware ──────────────────────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip preflight and health check
        if request.method == "OPTIONS" or request.url.path in ("/api/health", "/api/auth/login"):
            return await call_next(request)

        token = None
        header = request.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:]
        if not token:
            token = request.cookies.get("token")

        if not token:
            return JSONResponse({"error": "Authentication required"}, status_code=401)

        try:
            pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
            return JSONResponse({"error": "Invalid or expired token"}, status_code=401)

        return await call_next(request)


app.add_middleware(JWTMiddleware)


# ── Data store ──────────────────────────────────────────────────────────────
_COLOR_MAP = {
    "violet": "#7c3aed", "blue": "#3b82f6", "pink": "#ec4899",
    "amber": "#f59e0b",  "green": "#10b981", "red": "#ef4444",
    "cyan": "#06b6d4",   "orange": "#f97316", "yellow": "#eab308",
}


def _resolve_color(raw: str | None) -> str:
    if not raw:
        return "#64748b"
    return _COLOR_MAP.get(raw.lower(), raw)


def _format_program(p: dict) -> dict:
    """Map DB program row to the shape the frontend expects."""
    return {
        "id":          p["id"],
        "name":        p["name"],
        "subtitle":    p.get("level") or "",
        "type":        "After-school",
        "icon":        p.get("emoji") or "📚",
        "color":       _resolve_color(p.get("color")),
        "description": (
            f"{p['name']} · {p['site']} — {p['teacher']}"
            if p.get("site") and p.get("teacher")
            else p["name"]
        ),
        "site":        p.get("site"),
        "teacher":     p.get("teacher"),
        "schedule":    p.get("schedule"),
        # Live stats from DB
        "enrolled":        int(p.get("enrolled") or 0),
        "session_count":   int(p.get("session_count") or 0),
        "attendance_rate": float(p["attendance_rate"]) if p.get("attendance_rate") is not None else None,
        "live": int(p.get("session_count") or 0) > 0,
        # Historical fields — not in DB; kept for frontend compatibility
        "enrolled_2324":   None,
        "completed_2324":  None,
        "retention_2324":  None,
        "enrolled_2425":   int(p.get("enrolled") or 0),
    }


class DataStore:
    att:          pd.DataFrame = None
    work:         pd.DataFrame = None
    long_att:     pd.DataFrame = None
    session:      pd.DataFrame = None
    enroll:       pd.DataFrame = None
    retain:       pd.DataFrame = None
    demographics: pd.DataFrame = None
    perf:         pd.DataFrame = None
    programs:     list         = []


DS = DataStore()


@app.on_event("startup")
async def startup():
    try:
        DS.att      = get_attendance_df()
        DS.work     = load_work()
        DS.enroll, DS.retain = load_yearly()
        DS.long_att = get_attendance_long_df()
        DS.session  = get_session_trend_df()
        DS.demographics = generate_demographics(list(DS.att["student_id"].unique()))
        DS.perf     = student_performance_table(DS.att, DS.work)
        DS.programs = [_format_program(p) for p in get_programs()]
        print(f"✅ Data loaded: {len(DS.att)} students, {len(DS.session)} sessions, {len(DS.programs)} programs")
    except Exception as e:
        print(f"⚠️  DB unavailable at startup: {e}")
        print("    DataStore is empty — endpoints will return empty/zero data until DB is reachable.")
        # Leave all DS fields as None / [] — endpoints already guard against None DataFrames


def _df_to_records(df: pd.DataFrame) -> list:
    return json.loads(
        df.replace([np.nan, np.inf, -np.inf], None)
          .to_json(orient="records", date_format="iso")
    )


# ── Endpoints ───────────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
async def login(body: LoginBody):
    """
    Independent login endpoint. Reads users table via read-only DB.
    Issues JWT with same secret + payload format as Smart Attendance.
    No cross-service HTTP calls needed.
    """
    user = get_user_by_email(body.email.strip().lower())
    if not user or not _bcrypt.checkpw(
        body.password.encode(), user["password_hash"].encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "user_id": str(user["id"]),
        "email":   user["email"],
        "role":    user["role"],
        "exp":     datetime.now(timezone.utc) + timedelta(hours=8),
    }
    token = pyjwt.encode(payload, JWT_SECRET, algorithm="HS256")

    response = JSONResponse({
        "ok": True,
        "user": {
            "id":    str(user["id"]),
            "email": user["email"],
            "role":  user["role"],
            "name":  user.get("name"),
        },
    })
    response.set_cookie(
        "token",
        token,
        httponly=True,
        samesite="lax",
        max_age=8 * 3600,
        path="/",
    )
    return response


@app.get("/api/metrics")
def get_metrics():
    return overview_metrics(DS.att, DS.session)


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
        "attendance_asc":  ("Attendance %", True),
        "absences_desc":   ("Absent", False),
        "missing_desc":    ("% missing_num", False),
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
    return _df_to_records(attendance_distribution(DS.att))


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
    return _df_to_records(df) if not df.empty else []


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
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _build_system_prompt() -> str:
    metrics    = overview_metrics(DS.att, DS.session)
    teams_df   = team_performance(DS.perf)
    at_risk_df = at_risk_students(DS.perf)

    team_summary = ""
    if not teams_df.empty:
        for _, row in teams_df.iterrows():
            team_summary += (
                f"  - {row['Project Team Name']}: {row['Students']} students, "
                f"{row['Avg_Attendance']:.1f}% attendance, {row['Avg_Good']:.1f}% work quality\n"
            )

    at_risk_names = ""
    if not at_risk_df.empty:
        for _, row in at_risk_df.head(8).iterrows():
            at_risk_names += (
                f"  - {row['First Name']} {row['Last Name']}: "
                f"{row['Attendance %']:.1f}% attendance, Priority={row['Priority']}\n"
            )

    programs_summary = ""
    for p in DS.programs:
        rate = f"{p['attendance_rate']:.1f}%" if p["attendance_rate"] is not None else "no sessions yet"
        programs_summary += (
            f"  - {p['icon']} {p['name']} ({p['site']}): "
            f"{p['enrolled']} students enrolled, {p['session_count']} sessions, "
            f"attendance {rate}\n"
        )

    return f"""You are an expert education data analyst assistant for Urban Arts, a NYC youth arts program.
You have access to real program data from the live database.

LIVE DATA SUMMARY (all programs):
- Total students tracked: {metrics['total_students']}
- Average attendance across all sessions: {metrics['avg_attendance']:.1f}%
- Total sessions recorded: {metrics['sessions']}
- High performers (≥90% attendance): {metrics['high_performers']}
- Students needing attention (<70%): {metrics['low_performers']}
- Critical (<50% attendance): {metrics['critical_students']}

ACTIVE PROGRAMS:
{programs_summary or '  (no programs found)'}

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

Your role:
- Answer questions about attendance patterns, student performance, and program trends
- Provide actionable insights for program staff (not just statistics)
- Flag specific at-risk students when asked
- Suggest interventions based on data patterns
- Be concise, specific, and use actual numbers from the data above

Keep responses focused and under 250 words unless asked for detail."""


CHART_TOOL = {
    "type": "function",
    "function": {
        "name": "show_chart",
        "description": (
            "Display a visual chart or graph directly in the chat. "
            "Use this whenever the user asks for a graph, chart, or visualization, "
            "or when displaying data visually would be clearer than listing numbers."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["pie", "donut", "bar", "horizontal_bar", "line"],
                },
                "title": {"type": "string"},
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
                },
                "unit":    {"type": "string", "default": "%"},
                "insight": {"type": "string"},
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

            tool_calls_acc: dict[int, dict] = {}
            finish_reason = None

            async for chunk in stream:
                choice       = chunk.choices[0]
                finish_reason = choice.finish_reason

                if choice.delta.content:
                    yield f"data: {json.dumps({'content': choice.delta.content})}\n\n"

                if choice.delta.tool_calls:
                    for tc in choice.delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id":        tc.id or "",
                                "name":      tc.function.name if tc.function else "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_acc[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc.function.arguments

            if finish_reason == "tool_calls" and tool_calls_acc:
                for tc in tool_calls_acc.values():
                    if tc["name"] == "show_chart":
                        try:
                            args = json.loads(tc["arguments"])
                            yield f"data: {json.dumps({'type': 'chart', 'chart': args})}\n\n"

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
    demo = load_demographics_summary()
    # Replace hardcoded attendance_rates with real DB data
    try:
        real_rates = get_program_attendance_rates()
        if real_rates:
            demo["attendance_rates"] = [
                {"program": r["program"], "rate_2324": None, "rate_2425": float(r["rate"]) if r["rate"] is not None else None}
                for r in real_rates
            ]
    except Exception:
        pass  # keep hardcoded fallback if DB fails
    return demo


# ── Programs endpoints (DB-backed) ──────────────────────────────────────────

@app.get("/api/programs")
def get_programs_endpoint():
    if DS.programs:
        return DS.programs
    # Fallback: query DB directly if DataStore wasn't populated at startup
    try:
        return [_format_program(p) for p in get_programs()]
    except Exception:
        return []


@app.get("/api/program/{program_id}")
def get_program_detail(program_id: str):
    raw = get_program_by_id(program_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Program not found")

    prog = _format_program(raw)
    trend = get_session_trend_for_program(program_id)

    live_metrics = None
    if prog["live"]:
        live_metrics = {
            "total_students": int(raw.get("enrolled") or 0),
            "avg_attendance": float(raw["attendance_rate"]) if raw.get("attendance_rate") is not None else None,
            "at_risk": get_at_risk_for_program(program_id),
        }

    return {
        **prog,
        "live_metrics": live_metrics,
        "trend": trend,
        "race":   [],   # demographics not stored per-student in current schema
        "gender": [],
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "students": len(DS.att) if DS.att is not None else 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
