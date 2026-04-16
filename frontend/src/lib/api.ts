const BASE = "";

export async function fetchMetrics() {
  const res = await fetch(`${BASE}/api/metrics`, { cache: "no-store" });
  return res.json();
}

export async function fetchSessionTrend() {
  const res = await fetch(`${BASE}/api/session-trend`, { cache: "no-store" });
  return res.json();
}

export async function fetchStudents(params?: {
  min_att?: number;
  max_att?: number;
  team?: string;
  sort?: string;
}) {
  const q = new URLSearchParams();
  if (params?.min_att != null) q.set("min_att", String(params.min_att));
  if (params?.max_att != null) q.set("max_att", String(params.max_att));
  if (params?.team) q.set("team", params.team);
  if (params?.sort) q.set("sort", params.sort);
  const res = await fetch(`${BASE}/api/students?${q}`, { cache: "no-store" });
  return res.json();
}

export async function fetchTeams() {
  const res = await fetch(`${BASE}/api/teams`, { cache: "no-store" });
  return res.json();
}

export async function fetchAtRisk() {
  const res = await fetch(`${BASE}/api/at-risk`, { cache: "no-store" });
  return res.json();
}

export async function fetchAttDistribution() {
  const res = await fetch(`${BASE}/api/attendance-distribution`, { cache: "no-store" });
  return res.json();
}

export async function fetchLateAbsent() {
  const res = await fetch(`${BASE}/api/late-absent-correlation`, { cache: "no-store" });
  return res.json();
}

export async function fetchYearlyEnrollment() {
  const res = await fetch(`${BASE}/api/yearly-enrollment`, { cache: "no-store" });
  return res.json();
}

export async function fetchRoles() {
  const res = await fetch(`${BASE}/api/roles`, { cache: "no-store" });
  return res.json();
}

export async function fetchTrackPreference() {
  const res = await fetch(`${BASE}/api/track-preference`, { cache: "no-store" });
  return res.json();
}

export async function fetchTeamsList() {
  const res = await fetch(`${BASE}/api/teams-list`, { cache: "no-store" });
  return res.json();
}

export async function fetchDemographics() {
  const res = await fetch(`${BASE}/api/demographics`, { cache: "no-store" });
  return res.json();
}

export async function fetchPrograms() {
  const res = await fetch(`${BASE}/api/programs`, { cache: "no-store" });
  return res.json();
}

export async function fetchProgramDetail(programId: string) {
  const res = await fetch(`${BASE}/api/program/${programId}`, { cache: "no-store" });
  return res.json();
}

export async function fetchStudentSessions(studentId: string) {
  const res = await fetch(`${BASE}/api/student-sessions/${studentId}`, { cache: "no-store" });
  return res.json();
}

export type StreamEvent =
  | { type: "text"; content: string }
  | { type: "chart"; chart: ChartData }
  | { type: "error"; message: string };

export interface ChartData {
  chart_type: "pie" | "donut" | "bar" | "horizontal_bar" | "line";
  title: string;
  data: { label: string; value: number }[];
  unit?: string;
  insight?: string;
}

export async function* streamChat(
  messages: { role: string; content: string }[]
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Chat error" }));
    throw new Error(err.detail || "Chat error");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";            // keep incomplete line in buffer

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") return;

      try {
        const parsed = JSON.parse(raw);
        if (parsed.error) throw new Error(parsed.error);
        if (parsed.type === "chart") {
          yield { type: "chart", chart: parsed.chart };
        } else if (parsed.content) {
          yield { type: "text", content: parsed.content };
        }
      } catch (e: any) {
        if (e.message && e.message !== "Unexpected end of JSON input") {
          yield { type: "error", message: e.message };
          return;
        }
      }
    }
  }
}
