import { Pool } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var _piqPool: Pool | undefined;
}

function createPool(): Pool {
  if (!process.env.DATABASE_URL_READONLY) {
    throw new Error(
      "DATABASE_URL_READONLY is required. Do not use DATABASE_URL here — Program IQ must only connect with read-only credentials."
    );
  }
  return new Pool({
    connectionString: process.env.DATABASE_URL_READONLY,
    max: 10,
    ssl: { rejectUnauthorized: false },
  });
}

const pool: Pool = global._piqPool ?? createPool();
if (process.env.NODE_ENV !== "production") global._piqPool = pool;

export default pool;

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AttendanceRow {
  student_id: string;
  "Preferred Name": string;
  "Last Name": string;
  "Grad Yr": number | null;
  "# here": number;
  "# late": number;
  "# excused": number;
  "# afk": number;
  "# absent": number;
  Avg_num: number;
  Status: string;
}

export interface SessionRow {
  date: string;
  present: number;
  late: number;
  excused: number;
  absent: number;
  recorded: number;
  attendance_rate: number;
}

export interface AttendanceLongRow {
  student_id: string;
  "Preferred Name": string;
  "Last Name": string;
  session_date: string;
  attendance_status: string;
}

export interface DbProgram {
  id: string;
  name: string;
  level: string | null;
  site: string | null;
  teacher: string | null;
  teacher_phone: string | null;
  schedule: string | null;
  emoji: string | null;
  color: string | null;
  enrolled: number;
  session_count: number;
  attendance_rate: number | null;
  absent_count?: number;
  present_count?: number;
}

// ─── Query functions ─────────────────────────────────────────────────────────

export async function getAttendanceRows(): Promise<AttendanceRow[]> {
  const { rows } = await pool.query<AttendanceRow>(`
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
  `);
  return rows.map((r) => ({
    ...r,
    "# here": Number(r["# here"]) || 0,
    "# late": Number(r["# late"]) || 0,
    "# excused": Number(r["# excused"]) || 0,
    "# afk": Number(r["# afk"]) || 0,
    "# absent": Number(r["# absent"]) || 0,
    Avg_num: Number(r.Avg_num) || 0,
  }));
}

export async function getSessionTrendRows(): Promise<SessionRow[]> {
  const { rows } = await pool.query<{
    date: Date;
    present: string;
    late: string;
    excused: string;
    absent: string;
    recorded: string;
    attendance_rate: string;
  }>(`
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
  `);
  return rows.map((r) => ({
    date: r.date instanceof Date ? r.date.toISOString().slice(0, 10) : String(r.date),
    present: Number(r.present) || 0,
    late: Number(r.late) || 0,
    excused: Number(r.excused) || 0,
    absent: Number(r.absent) || 0,
    recorded: Number(r.recorded) || 0,
    attendance_rate: Number(r.attendance_rate) || 0,
  }));
}

export async function getAttendanceLongRows(): Promise<AttendanceLongRow[]> {
  const { rows } = await pool.query<{
    student_id: string;
    "Preferred Name": string;
    "Last Name": string;
    session_date: Date;
    attendance_status: string;
  }>(`
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
  `);
  return rows.map((r) => ({
    ...r,
    session_date:
      r.session_date instanceof Date
        ? r.session_date.toISOString().slice(0, 10)
        : String(r.session_date),
  }));
}

export async function getUserByEmail(
  email: string
): Promise<{ id: number; email: string; role: string; name: string | null; password_hash: string } | null> {
  const { rows } = await pool.query(
    "SELECT id, email, role, name, password_hash FROM users WHERE email = $1",
    [email.toLowerCase()]
  );
  return rows[0] ?? null;
}

export async function getPrograms(): Promise<DbProgram[]> {
  const { rows } = await pool.query<DbProgram>(`
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
  `);
  return rows.map((r) => ({
    ...r,
    enrolled: Number(r.enrolled) || 0,
    session_count: Number(r.session_count) || 0,
    attendance_rate: r.attendance_rate != null ? Number(r.attendance_rate) : null,
  }));
}

export async function getProgramById(programId: string): Promise<DbProgram | null> {
  const { rows } = await pool.query<DbProgram & { absent_count: string; present_count: string }>(`
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
    WHERE p.id = $1
    GROUP BY p.id
  `, [programId]);
  if (!rows[0]) return null;
  const r = rows[0];
  return {
    ...r,
    enrolled: Number(r.enrolled) || 0,
    session_count: Number(r.session_count) || 0,
    attendance_rate: r.attendance_rate != null ? Number(r.attendance_rate) : null,
    absent_count: Number(r.absent_count) || 0,
    present_count: Number(r.present_count) || 0,
  };
}

export async function getSessionTrendForProgram(programId: string): Promise<Array<{
  session: number;
  date: string;
  rate: number;
  present: number;
  recorded: number;
}>> {
  const { rows } = await pool.query<{
    date: Date;
    present: string;
    recorded: string;
    attendance_rate: string;
  }>(`
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
    WHERE s.program_id = $1 AND s.status = 'ended'
    GROUP BY s.date
    ORDER BY s.date
  `, [programId]);
  return rows.map((r, i) => ({
    session: i + 1,
    date: r.date instanceof Date ? r.date.toISOString().slice(0, 10) : String(r.date),
    rate: r.attendance_rate != null ? Number(r.attendance_rate) : 0,
    present: Number(r.present) || 0,
    recorded: Number(r.recorded) || 0,
  }));
}

export async function getProgramAttendanceRates(): Promise<Array<{ program: string; rate: number | null }>> {
  const { rows } = await pool.query<{ program: string; rate: string | null }>(`
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
  `);
  return rows.map((r) => ({
    program: r.program,
    rate: r.rate != null ? Number(r.rate) : null,
  }));
}

export async function getAtRiskForProgram(
  programId: string,
  threshold = 70.0
): Promise<number> {
  const { rows } = await pool.query<{ count: string }>(`
    SELECT COUNT(*) FROM (
        SELECT ar.student_code,
               COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
               / NULLIF(COUNT(*), 0) AS rate
        FROM attendance_records ar
        JOIN sessions s ON ar.session_id = s.id
        WHERE s.program_id = $1
        GROUP BY ar.student_code
        HAVING COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) * 100.0
               / NULLIF(COUNT(*), 0) < $2
    ) sub
  `, [programId, threshold]);
  return Number(rows[0]?.count) || 0;
}
