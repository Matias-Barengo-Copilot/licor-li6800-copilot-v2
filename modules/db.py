"""
Read-only DB connection and query functions for Program IQ.
Uses DATABASE_URL_READONLY — no fallback. Write credentials must never reach this module.
"""
import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
import psycopg2.extras

_readonly_url = os.environ.get("DATABASE_URL_READONLY", "")
if not _readonly_url:
    raise RuntimeError(
        "DATABASE_URL_READONLY is required. Set it in your .env before starting Program IQ. "
        "Do not use DATABASE_URL here — Program IQ must only connect with read-only credentials."
    )
DATABASE_URL = _readonly_url


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def get_attendance_df() -> pd.DataFrame:
    """
    Per-student attendance aggregates.
    Column names match analytics.py expectations.
    """
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT
              st.code                                               AS student_id,
              st.preferred_name                                     AS "Preferred Name",
              st.last_name                                          AS "Last Name",
              st.grad_yr                                            AS "Grad Yr",
              COUNT(CASE WHEN ar.status = 'Present' THEN 1 END)    AS "# here",
              COUNT(CASE WHEN ar.reason_code = 'L' THEN 1 END)     AS "# late",
              COUNT(CASE WHEN ar.reason_code = 'E' THEN 1 END)     AS "# excused",
              COUNT(CASE WHEN ar.reason_code = 'AFK' THEN 1 END)   AS "# afk",
              COUNT(CASE WHEN ar.status = 'Absent' THEN 1 END)     AS "# absent",
              ROUND(
                COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                / NULLIF(COUNT(*), 0), 1
              )                                                     AS "Avg_num",
              'Active'                                              AS "Status"
            FROM attendance_records ar
            JOIN students st ON ar.student_code = st.code
            JOIN sessions  s  ON ar.session_id  = s.id
            GROUP BY st.code, st.preferred_name, st.last_name, st.grad_yr
        """, conn)
        return df


def get_session_trend_df() -> pd.DataFrame:
    """Per-session attendance rates. Used by analytics.overview_metrics and session-trend endpoint."""
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT
              s.date,
              COUNT(CASE WHEN ar.status = 'Present' THEN 1 END)    AS present,
              COUNT(CASE WHEN ar.reason_code = 'L' THEN 1 END)     AS late,
              COUNT(CASE WHEN ar.reason_code = 'E' THEN 1 END)     AS excused,
              COUNT(CASE WHEN ar.status = 'Absent' THEN 1 END)     AS absent,
              COUNT(*)                                              AS recorded,
              ROUND(
                COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                / NULLIF(COUNT(*), 0), 1
              )                                                     AS attendance_rate
            FROM sessions s
            JOIN attendance_records ar ON ar.session_id = s.id
            WHERE s.status = 'ended'
            GROUP BY s.date
            ORDER BY s.date
        """, conn, parse_dates=["date"])
        return df


def get_attendance_long_df() -> pd.DataFrame:
    """Individual records in long format. Used by student session history endpoint."""
    with get_conn() as conn:
        df = pd.read_sql("""
            SELECT
              st.code             AS student_id,
              st.preferred_name   AS "Preferred Name",
              st.last_name        AS "Last Name",
              s.date              AS session_date,
              ar.status           AS attendance_status
            FROM attendance_records ar
            JOIN students st ON ar.student_code = st.code
            JOIN sessions  s  ON ar.session_id  = s.id
            ORDER BY st.code, s.date
        """, conn, parse_dates=["session_date"])
        return df


def get_attendance_rate(program_id: str = None) -> float:
    """Overall or per-program attendance rate (0–100)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if program_id:
                cur.execute("""
                    SELECT ROUND(
                      COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                      / NULLIF(COUNT(*), 0), 1
                    )
                    FROM attendance_records ar
                    JOIN sessions s ON ar.session_id = s.id
                    WHERE s.program_id = %s
                """, (program_id,))
            else:
                cur.execute("""
                    SELECT ROUND(
                      COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                      / NULLIF(COUNT(*), 0), 1
                    )
                    FROM attendance_records
                """)
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else 0.0


def get_at_risk_students(threshold: float = 70.0) -> list:
    """Students with attendance rate below threshold."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                  st.code, st.preferred_name, st.last_name,
                  ROUND(
                    COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0), 1
                  ) AS rate_pct
                FROM attendance_records ar
                JOIN students st ON ar.student_code = st.code
                GROUP BY st.code, st.preferred_name, st.last_name
                HAVING COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                       / NULLIF(COUNT(*), 0) < %s
                ORDER BY rate_pct
            """, (threshold,))
            return [dict(r) for r in cur.fetchall()]


def get_user_by_email(email: str) -> dict | None:
    """Return user row for login verification. Uses read-only connection — bcrypt check is local."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email.lower(),))
            row = cur.fetchone()
            return dict(row) if row else None


def get_programs() -> list:
    """All programs with live enrolled count and attendance rate from DB."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.id, p.name, p.level, p.site, p.teacher,
                    p.teacher_phone, p.schedule, p.emoji, p.color,
                    COUNT(DISTINCT sp.student_code)                        AS enrolled,
                    COUNT(DISTINCT s.id)                                   AS session_count,
                    ROUND(
                        COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                        / NULLIF(COUNT(ar.id), 0), 1
                    )                                                      AS attendance_rate
                FROM programs p
                LEFT JOIN student_programs sp ON sp.program_id = p.id
                LEFT JOIN sessions s          ON s.program_id  = p.id AND s.status = 'ended'
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                GROUP BY p.id
                ORDER BY p.name
            """)
            return [dict(r) for r in cur.fetchall()]


def get_program_by_id(program_id: str) -> dict | None:
    """Single program with full live metrics."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.id, p.name, p.level, p.site, p.teacher,
                    p.teacher_phone, p.schedule, p.emoji, p.color,
                    COUNT(DISTINCT sp.student_code)                        AS enrolled,
                    COUNT(DISTINCT s.id)                                   AS session_count,
                    ROUND(
                        COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                        / NULLIF(COUNT(ar.id), 0), 1
                    )                                                      AS attendance_rate,
                    COUNT(CASE WHEN ar.status = 'Absent' THEN 1 END)      AS absent_count,
                    COUNT(CASE WHEN ar.status = 'Present' THEN 1 END)     AS present_count
                FROM programs p
                LEFT JOIN student_programs sp ON sp.program_id = p.id
                LEFT JOIN sessions s          ON s.program_id  = p.id AND s.status = 'ended'
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                WHERE p.id = %s
                GROUP BY p.id
            """, (program_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_session_trend_for_program(program_id: str) -> list:
    """Per-session attendance trend for a specific program. Returns list of dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    s.date,
                    COUNT(CASE WHEN ar.status = 'Present' THEN 1 END)  AS present,
                    COUNT(*)                                             AS recorded,
                    ROUND(
                        COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                        / NULLIF(COUNT(*), 0), 1
                    )                                                    AS attendance_rate
                FROM sessions s
                JOIN attendance_records ar ON ar.session_id = s.id
                WHERE s.program_id = %s AND s.status = 'ended'
                GROUP BY s.date
                ORDER BY s.date
            """, (program_id,))
            rows = cur.fetchall()
            return [
                {
                    "session": i + 1,
                    "date": str(r["date"]),
                    "rate": float(r["attendance_rate"]) if r["attendance_rate"] is not None else 0.0,
                    "present": int(r["present"]),
                    "recorded": int(r["recorded"]),
                }
                for i, r in enumerate(rows)
            ]


def get_at_risk_for_program(program_id: str, threshold: float = 70.0) -> int:
    """Count of at-risk students (attendance below threshold) for a specific program."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM (
                    SELECT ar.student_code,
                           COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                           / NULLIF(COUNT(*), 0) AS rate
                    FROM attendance_records ar
                    JOIN sessions s ON ar.session_id = s.id
                    WHERE s.program_id = %s
                    GROUP BY ar.student_code
                    HAVING COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                           / NULLIF(COUNT(*), 0) < %s
                ) sub
            """, (program_id, threshold))
            row = cur.fetchone()
            return int(row[0]) if row else 0


def get_program_attendance_rates() -> list:
    """Real attendance rate per program — used by demographics section."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    p.name AS program,
                    ROUND(
                        COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
                        / NULLIF(COUNT(ar.id), 0), 1
                    ) AS rate
                FROM programs p
                LEFT JOIN sessions s ON s.program_id = p.id AND s.status = 'ended'
                LEFT JOIN attendance_records ar ON ar.session_id = s.id
                GROUP BY p.id, p.name
                ORDER BY p.name
            """)
            return [dict(r) for r in cur.fetchall()]
