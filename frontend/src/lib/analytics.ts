/**
 * Analytics: compute all key metrics from raw DB rows.
 * Ports analytics.py — no pandas, uses plain TypeScript + lodash.
 */
import groupBy from "lodash/groupBy";
import meanBy from "lodash/meanBy";
import sumBy from "lodash/sumBy";
import { AT_RISK_THRESHOLDS } from "./constants";
import type { AttendanceRow, SessionRow } from "./db";

// ─── Work row (currently empty — no DB table yet) ────────────────────────────
export interface WorkRow {
  student_id: string;
  "% good_num": number | null;
  "% needs work_num": number | null;
  "% missing_num": number | null;
  "Project Team Name": string | null;
  "Project Team Role": string | null;
  "Portfolio Project - Itch Link": string | null;
  "Art v. Programming": string | null;
}

// ─── Merged performance row ───────────────────────────────────────────────────
export interface PerfRow extends AttendanceRow {
  "% good_num": number | null;
  "% needs work_num": number | null;
  "% missing_num": number | null;
  "Project Team Name": string | null;
  "Project Team Role": string | null;
  "Portfolio Project - Itch Link": string | null;
  "Art v. Programming": string | null;
  "Attendance %": number;
  "First Name": string;
  Present: number;
  Late: number;
  Excused: number;
  AFK: number;
  Absent: number;
  "At Risk": boolean;
  Priority: "HIGH" | "MEDIUM" | "OK";
}

// ─── Overview metrics ─────────────────────────────────────────────────────────
export interface OverviewMetrics {
  total_students: number;
  avg_attendance: number;
  sessions: number;
  high_performers: number;
  low_performers: number;
  critical_students: number;
  recent_session_rate: number;
  recent_delta: number;
}

export function overviewMetrics(
  att: AttendanceRow[],
  session: SessionRow[]
): OverviewMetrics {
  const total = att.length;
  const avgAtt =
    total > 0 ? att.reduce((s, r) => s + (r.Avg_num || 0), 0) / total : 0;
  const sessions = session.length;

  const high = att.filter((r) => r.Avg_num >= 90).length;
  const low = att.filter((r) => r.Avg_num < AT_RISK_THRESHOLDS.attendance_low).length;
  const critical = att.filter(
    (r) => r.Avg_num < AT_RISK_THRESHOLDS.attendance_critical
  ).length;

  const nonZero = session.filter((s) => s.attendance_rate > 0);
  const recentRate =
    nonZero.length > 0 ? nonZero[nonZero.length - 1].attendance_rate : 0;
  const delta =
    nonZero.length >= 2
      ? nonZero[nonZero.length - 1].attendance_rate -
        nonZero[nonZero.length - 2].attendance_rate
      : 0;

  return {
    total_students: total,
    avg_attendance: Math.round(avgAtt * 10) / 10,
    sessions,
    high_performers: high,
    low_performers: low,
    critical_students: critical,
    recent_session_rate: Math.round(recentRate * 10) / 10,
    recent_delta: Math.round(delta * 10) / 10,
  };
}

// ─── Priority helper ──────────────────────────────────────────────────────────
function calcPriority(
  att: number,
  missing: number | null,
  absent: number
): "HIGH" | "MEDIUM" | "OK" {
  const m = missing ?? 0;
  if (att < AT_RISK_THRESHOLDS.attendance_critical || m > 70) return "HIGH";
  if (
    att < AT_RISK_THRESHOLDS.attendance_low ||
    m > AT_RISK_THRESHOLDS.missing_work_high ||
    absent > AT_RISK_THRESHOLDS.absences_high
  )
    return "MEDIUM";
  return "OK";
}

// ─── Student performance table ────────────────────────────────────────────────
export function studentPerformanceTable(
  attRows: AttendanceRow[],
  workRows: WorkRow[]
): PerfRow[] {
  const workMap = new Map(workRows.map((w) => [w.student_id, w]));

  const merged: PerfRow[] = attRows.map((a) => {
    const w = workMap.get(a.student_id);
    const attPct = a.Avg_num;
    const missing = w?.["% missing_num"] ?? null;
    const absent = a["# absent"];

    return {
      ...a,
      "First Name": a["Preferred Name"],
      "Attendance %": attPct,
      Present: a["# here"],
      Late: a["# late"],
      Excused: a["# excused"],
      AFK: a["# afk"],
      Absent: absent,
      "% good_num": w?.["% good_num"] ?? null,
      "% needs work_num": w?.["% needs work_num"] ?? null,
      "% missing_num": missing,
      "Project Team Name": w?.["Project Team Name"] ?? null,
      "Project Team Role": w?.["Project Team Role"] ?? null,
      "Portfolio Project - Itch Link": w?.["Portfolio Project - Itch Link"] ?? null,
      "Art v. Programming": w?.["Art v. Programming"] ?? null,
      "At Risk":
        attPct < AT_RISK_THRESHOLDS.attendance_low ||
        (missing !== null && missing > AT_RISK_THRESHOLDS.missing_work_high) ||
        absent > AT_RISK_THRESHOLDS.absences_high,
      Priority: calcPriority(attPct, missing, absent),
    };
  });

  return merged.sort((a, b) => b["Attendance %"] - a["Attendance %"]);
}

// ─── At-risk students ─────────────────────────────────────────────────────────
const PRIORITY_ORDER = { HIGH: 0, MEDIUM: 1, OK: 2 };

export function atRiskStudents(perf: PerfRow[]): PerfRow[] {
  return perf
    .filter((r) => r["At Risk"])
    .sort(
      (a, b) =>
        PRIORITY_ORDER[a.Priority] - PRIORITY_ORDER[b.Priority] ||
        a["Attendance %"] - b["Attendance %"]
    );
}

// ─── Team performance ─────────────────────────────────────────────────────────
export interface TeamRow {
  "Project Team Name": string;
  Students: number;
  Avg_Attendance: number;
  Avg_Good: number | null;
  Avg_Missing: number | null;
  Total_Absences: number;
}

export function teamPerformance(perf: PerfRow[]): TeamRow[] {
  const withTeam = perf.filter((r) => r["Project Team Name"]);
  if (!withTeam.length) return [];

  const groups = groupBy(withTeam, "Project Team Name");
  const result: TeamRow[] = Object.entries(groups).map(([team, rows]) => {
    const attVals = rows.map((r) => r["Attendance %"]);
    const goodVals = rows
      .map((r) => r["% good_num"])
      .filter((v): v is number => v != null);
    const missingVals = rows
      .map((r) => r["% missing_num"])
      .filter((v): v is number => v != null);

    return {
      "Project Team Name": team,
      Students: rows.length,
      Avg_Attendance:
        Math.round(
          (attVals.reduce((s, v) => s + v, 0) / attVals.length) * 10
        ) / 10,
      Avg_Good:
        goodVals.length > 0
          ? Math.round(
              (goodVals.reduce((s, v) => s + v, 0) / goodVals.length) * 10
            ) / 10
          : null,
      Avg_Missing:
        missingVals.length > 0
          ? Math.round(
              (missingVals.reduce((s, v) => s + v, 0) / missingVals.length) *
                10
            ) / 10
          : null,
      Total_Absences: rows.reduce((s, r) => s + r.Absent, 0),
    };
  });

  return result.sort((a, b) => b.Avg_Attendance - a.Avg_Attendance);
}

// ─── Attendance distribution ──────────────────────────────────────────────────
export interface BandRow {
  "Attendance Band": string;
  Students: number;
}

export function attendanceDistribution(att: AttendanceRow[]): BandRow[] {
  const bands = [
    { label: "<60%", min: 0, max: 60 },
    { label: "60–70%", min: 60, max: 70 },
    { label: "70–80%", min: 70, max: 80 },
    { label: "80–90%", min: 80, max: 90 },
    { label: "90–100%", min: 90, max: 101 },
  ];
  return bands.map((b) => ({
    "Attendance Band": b.label,
    Students: att.filter((r) => r.Avg_num >= b.min && r.Avg_num < b.max).length,
  }));
}

// ─── Late vs absent correlation ───────────────────────────────────────────────
export interface CorrelationResult {
  corr: number | null;
  data: Array<{
    "# late": number;
    "# absent": number;
    Name: string;
    Avg_num: number;
  }>;
}

export function lateVsAbsentCorrelation(att: AttendanceRow[]): CorrelationResult {
  const rows = att
    .filter((r) => r["# late"] != null && r["# absent"] != null)
    .map((r) => ({
      "# late": r["# late"],
      "# absent": r["# absent"],
      Name: `${r["Preferred Name"]} ${r["Last Name"]}`,
      Avg_num: r.Avg_num,
    }));

  if (rows.length < 3) return { corr: null, data: rows };

  // Pearson r
  const n = rows.length;
  const x = rows.map((r) => r["# late"]);
  const y = rows.map((r) => r["# absent"]);
  const mx = x.reduce((s, v) => s + v, 0) / n;
  const my = y.reduce((s, v) => s + v, 0) / n;
  const num = x.reduce((s, xi, i) => s + (xi - mx) * (y[i] - my), 0);
  const dx = Math.sqrt(x.reduce((s, xi) => s + (xi - mx) ** 2, 0));
  const dy = Math.sqrt(y.reduce((s, yi) => s + (yi - my) ** 2, 0));
  const corr = dx === 0 || dy === 0 ? null : Math.round((num / (dx * dy)) * 1000) / 1000;

  return { corr, data: rows };
}

// ─── Yearly enrollment trend ──────────────────────────────────────────────────
export interface YearlyRow {
  Program: string;
  Year: string;
  Enrolled: number;
}

export function yearlyEnrollmentTrend(enroll: Array<{
  Program: string;
  "2022_23": number | null;
  "2023_24": number | null;
  "2024_25": number | null;
}>): YearlyRow[] {
  const PROGRAMS = [
    "Summer Core",
    "After-school Core",
    "Advanced",
    "Studio",
    "Play Lab",
    "Senior XP (Summer)",
    "Spring Break Game Design Lab ",
  ];
  const filtered = enroll.filter((r) => PROGRAMS.includes(r.Program));
  const years: Array<[string, keyof typeof filtered[0]]> = [
    ["2022/23", "2022_23"],
    ["2023/24", "2023_24"],
    ["2024/25", "2024_25"],
  ];

  const result: YearlyRow[] = [];
  for (const row of filtered) {
    for (const [yearLabel, key] of years) {
      const val = row[key as "2022_23" | "2023_24" | "2024_25"];
      if (val != null) {
        result.push({ Program: row.Program, Year: yearLabel, Enrolled: Number(val) });
      }
    }
  }
  return result;
}

// ─── Role distribution ────────────────────────────────────────────────────────
export interface RoleRow {
  Role: string;
  Count: number;
}

export function roleDistribution(work: WorkRow[]): RoleRow[] {
  const roles = work
    .map((r) => r["Project Team Role"])
    .filter((r): r is string => r != null && r.trim() !== "");

  const counts = new Map<string, number>();
  for (const r of roles) {
    counts.set(r.trim(), (counts.get(r.trim()) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([Role, Count]) => ({ Role, Count }))
    .sort((a, b) => b.Count - a.Count);
}

// ─── Art vs programming ───────────────────────────────────────────────────────
export interface TrackRow {
  Track: string;
  Count: number;
}

export function artVsProgramming(work: WorkRow[]): TrackRow[] {
  const tracks = work
    .map((r) => r["Art v. Programming"])
    .filter((t): t is string => t != null && t.trim() !== "");

  const counts = new Map<string, number>();
  for (const t of tracks) {
    counts.set(t.trim(), (counts.get(t.trim()) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([Track, Count]) => ({ Track, Count }))
    .sort((a, b) => b.Count - a.Count);
}
