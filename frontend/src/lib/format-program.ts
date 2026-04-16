/**
 * Maps DB program row to the shape the frontend expects.
 * Ports _format_program() and _resolve_color() from server.py.
 */
import type { DbProgram } from "./db";

const COLOR_MAP: Record<string, string> = {
  violet: "#7c3aed",
  blue:   "#3b82f6",
  pink:   "#ec4899",
  amber:  "#f59e0b",
  green:  "#10b981",
  red:    "#ef4444",
  cyan:   "#06b6d4",
  orange: "#f97316",
  yellow: "#eab308",
};

export function resolveColor(raw: string | null | undefined): string {
  if (!raw) return "#64748b";
  return COLOR_MAP[raw.toLowerCase()] ?? raw;
}

export interface FormattedProgram {
  id: string;
  name: string;
  subtitle: string;
  type: string;
  icon: string;
  color: string;
  description: string;
  site: string | null;
  teacher: string | null;
  schedule: string | null;
  enrolled: number;
  session_count: number;
  attendance_rate: number | null;
  live: boolean;
  enrolled_2324: null;
  completed_2324: null;
  retention_2324: null;
  enrolled_2425: number;
}

export function formatProgram(p: DbProgram): FormattedProgram {
  return {
    id:          p.id,
    name:        p.name,
    subtitle:    p.level ?? "",
    type:        "After-school",
    icon:        p.emoji ?? "📚",
    color:       resolveColor(p.color),
    description:
      p.site && p.teacher
        ? `${p.name} · ${p.site} — ${p.teacher}`
        : p.name,
    site:        p.site,
    teacher:     p.teacher,
    schedule:    p.schedule,
    enrolled:        p.enrolled,
    session_count:   p.session_count,
    attendance_rate: p.attendance_rate,
    live:            p.session_count > 0,
    enrolled_2324:   null,
    completed_2324:  null,
    retention_2324:  null,
    enrolled_2425:   p.enrolled,
  };
}
