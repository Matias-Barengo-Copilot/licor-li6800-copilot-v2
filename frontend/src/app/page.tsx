"use client";

import { useEffect, useState, useCallback } from "react";
import dynamic from "next/dynamic";
import MetricCard from "@/components/MetricCard";
import AttendanceChart from "@/components/AttendanceChart";
import TeamChart from "@/components/TeamChart";
import DistributionChart from "@/components/DistributionChart";
import YearlyChart from "@/components/YearlyChart";
import DonutChart from "@/components/DonutChart";
import {
  fetchMetrics,
  fetchSessionTrend,
  fetchStudents,
  fetchTeams,
  fetchAtRisk,
  fetchAttDistribution,
  fetchYearlyEnrollment,
  fetchTeamsList,
  fetchDemographics,
  fetchPrograms,
  fetchProgramDetail,
} from "@/lib/api";

const ChatPanel = dynamic(() => import("@/components/ChatPanel"), { ssr: false });

// ── Nav ──────────────────────────────────────────────────────────────────
const NAV = [
  { id: "overview",     label: "Overview",     icon: "◈" },
  { id: "students",     label: "Students",     icon: "◉" },
  { id: "teams",        label: "Teams",        icon: "◆" },
  { id: "atrisk",       label: "At-Risk",      icon: "◐" },
  { id: "demographics", label: "Demographics", icon: "◍" },
  { id: "trends",       label: "Trends",       icon: "◇" },
  { id: "programs",     label: "Programs",     icon: "◭" },
];

// ── Priority badge ────────────────────────────────────────────────────────
function PriorityBadge({ p }: { p: string }) {
  const styles: Record<string, string> = {
    HIGH:   "background:#7f1d1d; color:#fca5a5;",
    MEDIUM: "background:#78350f; color:#fcd34d;",
    OK:     "background:#064e3b; color:#6ee7b7;",
  };
  return (
    <span
      className="text-xs font-semibold px-2 py-0.5 rounded-md"
      style={{ ...(Object.fromEntries((styles[p] || styles.OK).split(";").filter(Boolean).map(s => s.split(":").map(x=>x.trim()) as [string,string]))) }}
    >
      {p}
    </span>
  );
}

// ── Attendance badge ──────────────────────────────────────────────────────
function AttBadge({ v }: { v: number }) {
  const color = v >= 90 ? "#10b981" : v >= 70 ? "#f59e0b" : "#ef4444";
  return <span style={{ color, fontWeight: 700 }}>{v?.toFixed(1)}%</span>;
}

// ── Card wrapper ──────────────────────────────────────────────────────────
function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl p-5 ${className}`}
      style={{ background: "#13131f", border: "1px solid #252540" }}
    >
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold uppercase tracking-widest mb-4" style={{ color: "#64748b" }}>
      {children}
    </h2>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────
export default function Dashboard() {
  const [page, setPage] = useState("overview");
  const [chatOpen, setChatOpen] = useState(false);

  // Data states
  const [metrics, setMetrics] = useState<any>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [students, setStudents] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [atRisk, setAtRisk] = useState<any[]>([]);
  const [dist, setDist] = useState<any[]>([]);
  const [yearly, setYearly] = useState<any[]>([]);
  const [teamsList, setTeamsList] = useState<string[]>([]);
  const [demographics, setDemographics] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Programs
  const [programsList, setProgramsList] = useState<any[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<any>(null);
  const [programDetail, setProgramDetail] = useState<any>(null);
  const [programDetailLoading, setProgramDetailLoading] = useState(false);
  // Compare mode
  const [compareMode, setCompareMode] = useState(false);
  const [compareA, setCompareA] = useState<any>(null);
  const [compareB, setCompareB] = useState<any>(null);
  const [compareDetailA, setCompareDetailA] = useState<any>(null);
  const [compareDetailB, setCompareDetailB] = useState<any>(null);
  const [comparePicking, setComparePicking] = useState<"A" | "B" | null>(null);

  // Student filters
  const [minAtt, setMinAtt] = useState(0);
  const [maxAtt, setMaxAtt] = useState(100);
  const [teamFilter, setTeamFilter] = useState("All");
  const [sortBy, setSortBy] = useState("attendance_desc");
  const [search, setSearch] = useState("");

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [m, t, s, tm, ar, d, y, tl, demo, progs] = await Promise.all([
        fetchMetrics(),
        fetchSessionTrend(),
        fetchStudents(),
        fetchTeams(),
        fetchAtRisk(),
        fetchAttDistribution(),
        fetchYearlyEnrollment(),
        fetchTeamsList(),
        fetchDemographics(),
        fetchPrograms(),
      ]);
      setMetrics(m);
      setTrend(t);
      setStudents(s);
      setTeams(tm);
      setAtRisk(ar);
      setDist(d);
      setYearly(y);
      setTeamsList(tl);
      setDemographics(demo);
      setProgramsList(progs);
    } catch {
      setError("Cannot connect to backend. Make sure the Python server is running on port 8000.");
    }
    setLoading(false);
  }, []);

  async function openProgram(prog: any) {
    setSelectedProgram(prog);
    setCompareMode(false);
    setComparePicking(null);
    setProgramDetailLoading(true);
    try {
      const detail = await fetchProgramDetail(prog.id);
      setProgramDetail(detail);
    } catch {
      setProgramDetail(null);
    }
    setProgramDetailLoading(false);
  }

  async function startCompare() {
    setCompareMode(true);
    setSelectedProgram(null);
    setCompareA(null);
    setCompareB(null);
    setCompareDetailA(null);
    setCompareDetailB(null);
    setComparePicking("A");
  }

  async function pickForCompare(prog: any) {
    if (comparePicking === "A") {
      setCompareA(prog);
      setComparePicking("B");
      const detail = await fetchProgramDetail(prog.id);
      setCompareDetailA(detail);
    } else if (comparePicking === "B") {
      setCompareB(prog);
      setComparePicking(null);
      const detail = await fetchProgramDetail(prog.id);
      setCompareDetailB(detail);
    }
  }

  useEffect(() => { loadAll(); }, [loadAll]);

  // ── PDF Export ──────────────────────────────────────────────────────────
  function exportPDF() {
    const now = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
    const pageTitle = NAV.find(n => n.id === page)?.label || "Dashboard";

    // Build at-risk rows
    const atRiskRows = atRisk.slice(0, 10).map((s: any) => `
      <tr>
        <td>${s["First Name"]} ${s["Last Name"]}</td>
        <td style="color:${s["Attendance %"] < 50 ? "#ef4444" : "#f59e0b"}">${s["Attendance %"]?.toFixed(1)}%</td>
        <td>${s.Absent ?? 0}</td>
        <td>${s["% missing_num"] != null ? s["% missing_num"].toFixed(0) + "%" : "—"}</td>
        <td style="font-weight:bold;color:${s.Priority === "HIGH" ? "#ef4444" : "#f59e0b"}">${s.Priority}</td>
      </tr>`).join("");

    const teamRows = teams.map((t: any) => `
      <tr>
        <td>${t["Project Team Name"]}</td>
        <td>${t.Students}</td>
        <td style="color:${t.Avg_Attendance >= 85 ? "#059669" : t.Avg_Attendance >= 70 ? "#d97706" : "#dc2626"}">${t.Avg_Attendance?.toFixed(1)}%</td>
        <td>${t.Avg_Good?.toFixed(1)}%</td>
        <td>${t.Avg_Missing?.toFixed(1)}%</td>
      </tr>`).join("");

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Program IQ — ${pageTitle} Report</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 11pt; color: #1e293b; background: white; padding: 0; }
  @page { margin: 0.75in; size: letter; }
  .cover { text-align: center; padding: 60px 40px; border-bottom: 3px solid #ff6b35; margin-bottom: 32px; }
  .logo { display: inline-block; width: 48px; height: 48px; background: linear-gradient(135deg,#ff6b35,#7c3aed); border-radius: 12px; line-height: 48px; color: white; font-size: 20px; font-weight: bold; margin-bottom: 16px; }
  .cover h1 { font-size: 28pt; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; }
  .cover .sub { font-size: 13pt; color: #64748b; margin-top: 6px; }
  .cover .date { font-size: 10pt; color: #94a3b8; margin-top: 12px; }
  .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 28px; }
  .kpi { border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 14px; text-align: center; }
  .kpi .val { font-size: 22pt; font-weight: 800; }
  .kpi .lbl { font-size: 8pt; color: #64748b; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.5px; }
  h2 { font-size: 13pt; font-weight: 700; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px; margin-bottom: 14px; margin-top: 28px; }
  table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
  th { background: #f8fafc; border-bottom: 2px solid #e2e8f0; padding: 8px 10px; text-align: left; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; }
  td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; }
  .section { margin-bottom: 28px; }
  .program-row { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .prog-card { flex: 1; min-width: 120px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
  .prog-card .name { font-weight: 700; font-size: 10pt; }
  .prog-card .stat { font-size: 15pt; font-weight: 800; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 8pt; color: #94a3b8; display: flex; justify-content: space-between; }
  .tag { display: inline-block; background: #fef3c7; color: #92400e; border-radius: 4px; padding: 1px 6px; font-size: 7.5pt; font-weight: 600; }
</style>
</head>
<body>
<div class="cover">
  <div class="logo">IQ</div>
  <h1>Program IQ</h1>
  <div class="sub">Urban Arts · 3D Game Design · School Year 2025/26</div>
  <div class="date">Generated on ${now} · ${pageTitle} View</div>
</div>

<div class="section">
  <h2>Program Overview</h2>
  <div class="kpi-grid">
    <div class="kpi"><div class="val" style="color:#f97316">${metrics?.total_students ?? "—"}</div><div class="lbl">Total Students</div></div>
    <div class="kpi"><div class="val" style="color:#059669">${metrics?.avg_attendance?.toFixed(1) ?? "—"}%</div><div class="lbl">Avg Attendance</div></div>
    <div class="kpi"><div class="val" style="color:#7c3aed">${metrics?.sessions ?? "—"}</div><div class="lbl">Sessions</div></div>
    <div class="kpi"><div class="val" style="color:#059669">${metrics?.high_performers ?? "—"}</div><div class="lbl">High Performers</div></div>
    <div class="kpi"><div class="val" style="color:#dc2626">${metrics?.low_performers ?? "—"}</div><div class="lbl">Need Attention</div></div>
  </div>
</div>

${atRisk.length > 0 ? `
<div class="section">
  <h2>At-Risk Students <span class="tag">${atRisk.length} flagged</span></h2>
  <table>
    <thead><tr><th>Student</th><th>Attendance</th><th>Absences</th><th>Missing Work</th><th>Priority</th></tr></thead>
    <tbody>${atRiskRows}</tbody>
  </table>
</div>` : ""}

${teams.length > 0 ? `
<div class="section">
  <h2>Project Team Performance</h2>
  <table>
    <thead><tr><th>Team</th><th>Students</th><th>Avg Attendance</th><th>Work Quality</th><th>Missing Work</th></tr></thead>
    <tbody>${teamRows}</tbody>
  </table>
</div>` : ""}

<div class="section">
  <h2>Program Retention Summary (SY2024-25)</h2>
  <div class="program-row">
    ${[
      { name: "Summer Core", enrolled: 96, pct: 93 },
      { name: "After-school Core", enrolled: 99, pct: 69 },
      { name: "3D Game Dev", enrolled: 90, pct: 82 },
      { name: "Studio", enrolled: 29, pct: 97 },
      { name: "Play Lab", enrolled: 8, pct: 88 },
      { name: "Senior XP", enrolled: 22, pct: 82 },
    ].map(p => `<div class="prog-card"><div class="name">${p.name}</div><div class="stat" style="color:${p.pct >= 90 ? "#059669" : p.pct >= 75 ? "#d97706" : "#dc2626"}">${p.pct}%</div><div class="lbl" style="font-size:8pt;color:#64748b">${p.enrolled} enrolled</div></div>`).join("")}
  </div>
</div>

<div class="footer">
  <span>Program IQ · Urban Arts · Confidential</span>
  <span>Printed ${now}</span>
</div>
</body>
</html>`;

    const win = window.open("", "_blank");
    if (win) {
      win.document.write(html);
      win.document.close();
      setTimeout(() => win.print(), 400);
    }
  }

  // Re-fetch students when filters change
  useEffect(() => {
    fetchStudents({ min_att: minAtt, max_att: maxAtt, team: teamFilter, sort: sortBy })
      .then(setStudents)
      .catch(() => {});
  }, [minAtt, maxAtt, teamFilter, sortBy]);

  // Filtered students by search
  const filteredStudents = students.filter((s) => {
    if (!search) return true;
    const name = `${s["First Name"] || ""} ${s["Last Name"] || ""}`.toLowerCase();
    return name.includes(search.toLowerCase());
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "#0a0a14" }}>
        <div className="text-center">
          <div className="text-4xl mb-4">🎮</div>
          <p className="text-lg font-semibold" style={{ color: "#ff6b35" }}>Loading Program IQ…</p>
          <p className="text-sm mt-1" style={{ color: "#64748b" }}>Connecting to data backend</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen" style={{ background: "#0a0a14" }}>
        <div
          className="text-center max-w-md rounded-2xl p-8"
          style={{ background: "#13131f", border: "1px solid #ef444440" }}
        >
          <div className="text-4xl mb-4">⚠️</div>
          <p className="font-semibold mb-2" style={{ color: "#ef4444" }}>Backend Not Running</p>
          <p className="text-sm mb-4" style={{ color: "#94a3b8" }}>{error}</p>
          <code className="block text-xs p-3 rounded-lg mb-4" style={{ background: "#0a0a14", color: "#10b981" }}>
            cd program-iq && python3 server.py
          </code>
          <button
            onClick={loadAll}
            className="px-6 py-2 rounded-xl font-semibold text-sm"
            style={{ background: "#ff6b35", color: "white" }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#0a0a14" }}>

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside
        className="w-56 flex-shrink-0 flex flex-col py-6"
        style={{ background: "#0d0d1a", borderRight: "1px solid #252540" }}
      >
        {/* Logo */}
        <div className="px-5 mb-8">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold"
              style={{ background: "linear-gradient(135deg, #ff6b35, #7c3aed)", color: "white" }}
            >
              IQ
            </div>
            <div>
              <p className="text-sm font-bold" style={{ color: "#e2e8f0" }}>Program IQ</p>
              <p className="text-xs" style={{ color: "#475569" }}>Urban Arts</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 space-y-1">
          {NAV.map((n) => {
            const active = page === n.id;
            return (
              <button
                key={n.id}
                onClick={() => setPage(n.id)}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all"
                style={
                  active
                    ? { background: "#ff6b3520", color: "#ff6b35", borderLeft: "2px solid #ff6b35" }
                    : { color: "#64748b" }
                }
              >
                <span className="text-base">{n.icon}</span>
                {n.label}
                {n.id === "atrisk" && atRisk.length > 0 && (
                  <span
                    className="ml-auto text-xs px-2 py-0.5 rounded-full font-bold"
                    style={{ background: "#ef444420", color: "#ef4444" }}
                  >
                    {atRisk.length}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom stats */}
        {metrics && (
          <div className="px-5 pt-4" style={{ borderTop: "1px solid #252540" }}>
            {/* Export PDF button */}
            <button
              onClick={exportPDF}
              className="w-full mb-4 flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all hover:opacity-80"
              style={{ background: "#ff6b3518", border: "1px solid #ff6b3540", color: "#ff6b35" }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
              </svg>
              Export PDF Report
            </button>
            <p className="text-xs mb-3" style={{ color: "#475569" }}>Quick Stats</p>
            {[
              ["Students", metrics.total_students],
              ["Sessions", metrics.sessions],
              ["Avg Att.", `${metrics.avg_attendance?.toFixed(1)}%`],
            ].map(([k, v]) => (
              <div key={String(k)} className="flex justify-between text-xs py-1">
                <span style={{ color: "#64748b" }}>{k}</span>
                <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* ── Main Content ─────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8">

          {/* ════════════════════════════════════════════════════════════════
              PAGE: OVERVIEW
          ════════════════════════════════════════════════════════════════ */}
          {page === "overview" && metrics && (
            <div className="space-y-6">
              {/* Header */}
              <div>
                <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>
                  Program Overview
                </h1>
                <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                  Urban Arts · 3D Game Design · School Year 2025/26
                </p>
              </div>

              {/* KPI Row */}
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                <MetricCard label="Total Students"  value={metrics.total_students}       accent="orange" icon="🎓" />
                <MetricCard label="Avg Attendance"  value={`${metrics.avg_attendance?.toFixed(1)}%`} accent="green" icon="✅" sub={`Last session ${metrics.recent_session_rate?.toFixed(0)}%`} />
                <MetricCard label="Sessions"        value={metrics.sessions}             accent="purple" icon="📅" />
                <MetricCard label="High Performers" value={metrics.high_performers}      accent="green"  icon="⭐" sub="≥90% attendance" />
                <MetricCard label="Need Attention"  value={metrics.low_performers}       accent="red"    icon="⚠️" sub={`${metrics.critical_students} critical`} />
              </div>

              {/* Trend + Distribution */}
              <div className="grid grid-cols-3 gap-5">
                <Card className="col-span-2">
                  <SectionTitle>Attendance Rate — School Year</SectionTitle>
                  <AttendanceChart data={trend} />
                </Card>
                <Card>
                  <SectionTitle>Distribution by Band</SectionTitle>
                  <DistributionChart data={dist} />
                </Card>
              </div>

              {/* Teams snapshot */}
              {teams.length > 0 && (
                <Card>
                  <SectionTitle>Project Teams Snapshot</SectionTitle>
                  <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                    {teams.map((t: any) => {
                      const att = t.Avg_Attendance;
                      const color = att >= 85 ? "#10b981" : att >= 70 ? "#f59e0b" : "#ef4444";
                      return (
                        <div
                          key={t["Project Team Name"]}
                          className="rounded-xl p-4"
                          style={{ background: "#1a1a2e", border: "1px solid #252540" }}
                        >
                          <p className="text-xs font-semibold truncate mb-3" style={{ color: "#e2e8f0" }}>
                            {t["Project Team Name"]}
                          </p>
                          <p className="text-2xl font-bold" style={{ color }}>{att?.toFixed(1)}%</p>
                          <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                            {t.Students} students · {t.Avg_Good?.toFixed(0)}% quality
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════
              PAGE: STUDENTS
          ════════════════════════════════════════════════════════════════ */}
          {page === "students" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>Student Performance</h1>

              {/* Filters */}
              <Card>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{ color: "#64748b" }}>
                      Search
                    </label>
                    <input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Student name…"
                      className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                      style={{ background: "#0a0a14", border: "1px solid #252540", color: "#e2e8f0" }}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{ color: "#64748b" }}>
                      Team
                    </label>
                    <select
                      value={teamFilter}
                      onChange={(e) => setTeamFilter(e.target.value)}
                      className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                      style={{ background: "#0a0a14", border: "1px solid #252540", color: "#e2e8f0" }}
                    >
                      <option value="All">All Teams</option>
                      {teamsList.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{ color: "#64748b" }}>
                      Sort By
                    </label>
                    <select
                      value={sortBy}
                      onChange={(e) => setSortBy(e.target.value)}
                      className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                      style={{ background: "#0a0a14", border: "1px solid #252540", color: "#e2e8f0" }}
                    >
                      <option value="attendance_desc">Attendance ↑</option>
                      <option value="attendance_asc">Attendance ↓</option>
                      <option value="absences_desc">Most Absences</option>
                      <option value="missing_desc">Most Missing Work</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium mb-1.5 block" style={{ color: "#64748b" }}>
                      Min Attendance: {minAtt}%
                    </label>
                    <input
                      type="range" min={0} max={100} step={5}
                      value={minAtt}
                      onChange={(e) => setMinAtt(Number(e.target.value))}
                      className="w-full accent-orange-500"
                    />
                  </div>
                </div>
              </Card>

              {/* Table */}
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <SectionTitle>Students — {filteredStudents.length} shown</SectionTitle>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr style={{ borderBottom: "1px solid #252540" }}>
                        {["Name", "Attendance", "Present", "Late", "Absent", "Work Quality", "Missing", "Team", "Role", "Status"].map((h) => (
                          <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "#475569" }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredStudents.map((s: any, i) => (
                        <tr
                          key={i}
                          className="transition-colors hover:bg-white/[0.02]"
                          style={{ borderBottom: "1px solid #1a1a2e" }}
                        >
                          <td className="py-2.5 px-3 font-medium" style={{ color: "#e2e8f0" }}>
                            {s["First Name"]} {s["Last Name"]}
                          </td>
                          <td className="py-2.5 px-3">
                            <AttBadge v={s["Attendance %"]} />
                          </td>
                          <td className="py-2.5 px-3" style={{ color: "#94a3b8" }}>{s.Present}</td>
                          <td className="py-2.5 px-3" style={{ color: "#f59e0b" }}>{s.Late}</td>
                          <td className="py-2.5 px-3" style={{ color: "#ef4444" }}>{s.Absent}</td>
                          <td className="py-2.5 px-3" style={{ color: "#7c3aed" }}>
                            {s["% good_num"] != null ? `${s["% good_num"]?.toFixed(0)}%` : "—"}
                          </td>
                          <td className="py-2.5 px-3" style={{ color: "#f97316" }}>
                            {s["% missing_num"] != null ? `${s["% missing_num"]?.toFixed(0)}%` : "—"}
                          </td>
                          <td className="py-2.5 px-3 text-xs" style={{ color: "#64748b" }}>
                            {s["Project Team Name"] || "—"}
                          </td>
                          <td className="py-2.5 px-3 text-xs" style={{ color: "#64748b" }}>
                            {s["Project Team Role"] || "—"}
                          </td>
                          <td className="py-2.5 px-3">
                            <PriorityBadge p={s.Priority || "OK"} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════
              PAGE: TEAMS
          ════════════════════════════════════════════════════════════════ */}
          {page === "teams" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>Team Analysis</h1>

              {/* Team cards */}
              {teams.length > 0 && (
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                  {teams.map((t: any) => {
                    const att = t.Avg_Attendance;
                    const attColor = att >= 85 ? "#10b981" : att >= 70 ? "#f59e0b" : "#ef4444";
                    return (
                      <Card key={t["Project Team Name"]}>
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <p className="font-bold text-base" style={{ color: "#e2e8f0" }}>
                              {t["Project Team Name"]}
                            </p>
                            <p className="text-xs mt-0.5" style={{ color: "#64748b" }}>
                              {t.Students} students
                            </p>
                          </div>
                          <span
                            className="text-xs px-2 py-1 rounded-lg font-semibold"
                            style={{ background: `${attColor}20`, color: attColor }}
                          >
                            {att?.toFixed(1)}%
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          {[
                            { label: "Attendance", value: `${att?.toFixed(1)}%`, color: attColor },
                            { label: "Work Quality", value: `${t.Avg_Good?.toFixed(1)}%`, color: "#7c3aed" },
                            { label: "Missing", value: `${t.Avg_Missing?.toFixed(1)}%`, color: "#ef4444" },
                          ].map((m) => (
                            <div key={m.label} className="text-center rounded-xl p-2" style={{ background: "#0a0a14" }}>
                              <p className="text-lg font-bold" style={{ color: m.color }}>{m.value}</p>
                              <p className="text-xs" style={{ color: "#64748b" }}>{m.label}</p>
                            </div>
                          ))}
                        </div>
                      </Card>
                    );
                  })}
                </div>
              )}

              {/* Team comparison chart */}
              {teams.length > 0 && (
                <Card>
                  <SectionTitle>Team Comparison — Attendance vs Work Quality</SectionTitle>
                  <TeamChart teams={teams} />
                </Card>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════
              PAGE: AT-RISK
          ════════════════════════════════════════════════════════════════ */}
          {page === "atrisk" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-bold" style={{ color: "#ef4444" }}>⚠️ At-Risk Students</h1>
                <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                  Flagged by: attendance &lt;70% OR missing work &gt;50% OR absences &gt;8
                </p>
              </div>

              {/* Summary KPIs */}
              <div className="grid grid-cols-3 gap-4">
                <MetricCard label="Total At-Risk" value={atRisk.length} accent="red" icon="🚨" />
                <MetricCard label="HIGH Priority"   value={atRisk.filter((s: any) => s.Priority === "HIGH").length}   accent="red"    icon="🔴" sub="Immediate action" />
                <MetricCard label="MEDIUM Priority" value={atRisk.filter((s: any) => s.Priority === "MEDIUM").length} accent="yellow" icon="🟡" sub="Monitor closely" />
              </div>

              {atRisk.length === 0 ? (
                <Card>
                  <div className="text-center py-12">
                    <p className="text-4xl mb-4">🎉</p>
                    <p className="font-semibold" style={{ color: "#10b981" }}>
                      No at-risk students detected!
                    </p>
                    <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                      All students are meeting attendance benchmarks.
                    </p>
                  </div>
                </Card>
              ) : (
                <div className="space-y-3">
                  {atRisk.map((s: any, i) => {
                    const borderColor = s.Priority === "HIGH" ? "#7f1d1d" : "#78350f";
                    return (
                      <div
                        key={i}
                        className="rounded-2xl p-5 flex items-center justify-between gap-4 flex-wrap"
                        style={{ background: "#13131f", border: `1px solid ${borderColor}` }}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <p className="font-semibold" style={{ color: "#e2e8f0" }}>
                              {s["First Name"]} {s["Last Name"]}
                            </p>
                            <PriorityBadge p={s.Priority} />
                          </div>
                          <p className="text-xs" style={{ color: "#64748b" }}>
                            Team: {s["Project Team Name"] || "—"} · Role: {s["Project Team Role"] || "—"}
                          </p>
                        </div>
                        <div className="flex gap-6 flex-shrink-0">
                          {[
                            { label: "Attendance", value: `${s["Attendance %"]?.toFixed(1)}%`, color: "#ef4444" },
                            { label: "Absences",   value: s.Absent,                            color: "#f97316" },
                            { label: "Late",       value: s.Late,                              color: "#f59e0b" },
                            { label: "Missing Work", value: `${s["% missing_num"]?.toFixed(0) ?? 0}%`, color: "#8b5cf6" },
                          ].map((m) => (
                            <div key={m.label} className="text-center">
                              <p className="text-xl font-bold" style={{ color: m.color }}>{m.value}</p>
                              <p className="text-xs" style={{ color: "#64748b" }}>{m.label}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════
              PAGE: DEMOGRAPHICS
          ════════════════════════════════════════════════════════════════ */}
          {page === "demographics" && demographics && (
            <div className="space-y-6">
              <div>
                <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>Demographics</h1>
                <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                  SY2023-24 actuals · 2024-25 projected proportionally from source data
                </p>
              </div>

              {/* Enrollment KPIs */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard label="Enrolled SY2023-24" value={demographics.enrollment_2324} accent="purple" icon="📋" />
                <MetricCard label="Enrolled SY2024-25" value={demographics.enrollment_2425} accent="orange" icon="📈" sub="GA programs only" />
                <MetricCard label="With Disability" value="7%" accent="yellow" icon="♿" sub={`~${demographics.disability?.[0]?.n_2425} students`} />
                <MetricCard label="Low Income (<$75k)" value="67%" accent="green" icon="🏠" sub="of enrolled students" />
              </div>

              {/* Race + Gender row */}
              <div className="grid grid-cols-2 gap-5">
                <Card>
                  <SectionTitle>Race / Ethnicity (2024-25 projected)</SectionTitle>
                  <DonutChart data={demographics.race} height={280} />
                  <div className="mt-3 space-y-1.5">
                    {demographics.race.filter((r: any) => r.pct_2425 > 0).map((r: any) => (
                      <div key={r.category} className="flex items-center justify-between text-xs">
                        <span style={{ color: "#94a3b8" }}>{r.category}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>
                          {r.pct_2425}% · {r.n_2425} students
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <SectionTitle>Gender Identity (2024-25 projected)</SectionTitle>
                  <DonutChart data={demographics.gender} height={280} />
                  <div className="mt-3 space-y-1.5">
                    {demographics.gender.filter((g: any) => g.pct_2425 > 0).map((g: any) => (
                      <div key={g.category} className="flex items-center justify-between text-xs">
                        <span style={{ color: "#94a3b8" }}>{g.category}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>
                          {g.pct_2425}% · {g.n_2425} students
                        </span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Grade + Income + Location */}
              <div className="grid grid-cols-3 gap-5">
                <Card>
                  <SectionTitle>Grade Level</SectionTitle>
                  {demographics.grade.map((g: any) => (
                    <div key={g.category} className="mb-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span style={{ color: "#94a3b8" }}>{g.category}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{g.pct_2425}% · {g.n_2425}</span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                        <div className="h-full rounded-full" style={{ width: `${g.pct_2425}%`, background: "#ff6b35" }} />
                      </div>
                    </div>
                  ))}
                </Card>

                <Card>
                  <SectionTitle>Family Income</SectionTitle>
                  {demographics.income.map((inc: any) => (
                    <div key={inc.category} className="mb-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span style={{ color: "#94a3b8" }}>{inc.category}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{inc.pct_2425}% · {inc.n_2425}</span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                        <div className="h-full rounded-full" style={{ width: `${inc.pct_2425}%`, background: "#7c3aed" }} />
                      </div>
                    </div>
                  ))}
                </Card>

                <Card>
                  <SectionTitle>School Location</SectionTitle>
                  {demographics.location.map((loc: any) => (
                    <div key={loc.category} className="mb-3">
                      <div className="flex justify-between text-xs mb-1">
                        <span style={{ color: "#94a3b8" }}>{loc.category}</span>
                        <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{loc.pct_2324}% · {loc.n_2425}</span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                        <div className="h-full rounded-full" style={{ width: `${loc.pct_2324}%`, background: "#10b981" }} />
                      </div>
                    </div>
                  ))}
                </Card>
              </div>

              {/* Attendance rates by program */}
              <Card>
                <SectionTitle>Attendance Rates by Program</SectionTitle>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid #252540" }}>
                      {["Program", "SY2023-24", "SY2024-25 (assumed)"].map((h) => (
                        <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "#475569" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {demographics.attendance_rates.map((r: any) => (
                      <tr key={r.program} style={{ borderBottom: "1px solid #1a1a2e" }} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 px-3" style={{ color: "#e2e8f0" }}>{r.program}</td>
                        <td className="py-2.5 px-3" style={{ color: r.rate_2324 ? "#94a3b8" : "#475569" }}>
                          {r.rate_2324 != null ? `${r.rate_2324}%` : "—"}
                        </td>
                        <td className="py-2.5 px-3 font-bold" style={{ color: r.rate_2425 >= 90 ? "#10b981" : r.rate_2425 >= 80 ? "#f59e0b" : "#ef4444" }}>
                          {r.rate_2425}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>

              {/* Data note */}
              <div className="rounded-xl px-5 py-3 text-xs" style={{ background: "#1a1a2e", border: "1px solid #252540", color: "#64748b" }}>
                ℹ️ {demographics.note}
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════
              PAGE: TRENDS
          ════════════════════════════════════════════════════════════════ */}
          {page === "trends" && (
            <div className="space-y-6">
              <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>Program Trends</h1>

              {/* Historical highlight KPIs */}
              <div className="grid grid-cols-3 gap-4">
                <MetricCard label="Total Students 2024/25" value="668"  accent="orange" icon="📊" sub="All programs combined" />
                <MetricCard label="3D Game Dev Growth"     value="+55%" accent="purple" icon="📈" sub="2023/24 → 2024/25" />
                <MetricCard label="Best Retention"         value="97%"  accent="green"  icon="🏆" sub="Studio program" />
              </div>

              {/* Yearly enrollment */}
              {yearly.length > 0 && (
                <Card>
                  <SectionTitle>Multi-Year Enrollment by Program</SectionTitle>
                  <YearlyChart data={yearly} />
                </Card>
              )}

              {/* Session trend */}
              <Card>
                <SectionTitle>Current Year — Session Attendance</SectionTitle>
                <AttendanceChart data={trend} />
              </Card>

              {/* Retention summary table */}
              <Card>
                <SectionTitle>Retention Highlights (2024/25)</SectionTitle>
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: "1px solid #252540" }}>
                      {["Program", "Enrolled", "Completed", "Retention %"].map((h) => (
                        <th key={h} className="text-left py-2 px-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "#475569" }}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { name: "Summer Core (2D Game Dev)", enrolled: 96, completed: 89, pct: 93 },
                      { name: "After-school Core", enrolled: 99, completed: 68, pct: 69 },
                      { name: "3D Game Dev", enrolled: 90, completed: 74, pct: 82 },
                      { name: "Studio", enrolled: 29, completed: 28, pct: 97 },
                      { name: "Play Lab", enrolled: 8, completed: 7, pct: 88 },
                      { name: "Senior XP", enrolled: 22, completed: 18, pct: 82 },
                      { name: "Spring Break Lab", enrolled: 51, completed: 37, pct: 73 },
                    ].map((r) => {
                      const color = r.pct >= 90 ? "#10b981" : r.pct >= 75 ? "#f59e0b" : "#ef4444";
                      return (
                        <tr key={r.name} style={{ borderBottom: "1px solid #1a1a2e" }} className="hover:bg-white/[0.02]">
                          <td className="py-2.5 px-3" style={{ color: "#e2e8f0" }}>{r.name}</td>
                          <td className="py-2.5 px-3" style={{ color: "#94a3b8" }}>{r.enrolled}</td>
                          <td className="py-2.5 px-3" style={{ color: "#94a3b8" }}>{r.completed}</td>
                          <td className="py-2.5 px-3 font-bold" style={{ color }}>{r.pct}%</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </Card>
            </div>
          )}
          {/* ════════════════════════════════════════════════════════════════
              PAGE: PROGRAMS
          ════════════════════════════════════════════════════════════════ */}
          {page === "programs" && (
            <div className="space-y-6">
              {/* Header row */}
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-bold" style={{ color: "#e2e8f0" }}>
                    {selectedProgram && !compareMode
                      ? `${selectedProgram.icon} ${selectedProgram.name}`
                      : compareMode
                      ? "Compare Programs"
                      : "Programs"}
                  </h1>
                  <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                    {selectedProgram && !compareMode
                      ? selectedProgram.description
                      : compareMode
                      ? comparePicking ? `Select program ${comparePicking} to compare` : "Side-by-side comparison"
                      : "Urban Arts · All programs · SY2023-24 actuals"}
                  </p>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  {(selectedProgram || compareMode) && (
                    <button
                      onClick={() => { setSelectedProgram(null); setCompareMode(false); setComparePicking(null); }}
                      className="px-4 py-2 rounded-xl text-sm font-medium transition-colors hover:opacity-80"
                      style={{ background: "#1a1a2e", border: "1px solid #252540", color: "#94a3b8" }}
                    >
                      ← All Programs
                    </button>
                  )}
                  {!compareMode && !selectedProgram && (
                    <button
                      onClick={startCompare}
                      className="px-4 py-2 rounded-xl text-sm font-semibold transition-colors hover:opacity-80"
                      style={{ background: "#7c3aed20", border: "1px solid #7c3aed40", color: "#a78bfa" }}
                    >
                      ⇄ Compare Programs
                    </button>
                  )}
                  {compareMode && !comparePicking && compareA && compareB && (
                    <button
                      onClick={() => { setCompareA(null); setCompareB(null); setCompareDetailA(null); setCompareDetailB(null); setComparePicking("A"); }}
                      className="px-4 py-2 rounded-xl text-sm font-medium transition-colors hover:opacity-80"
                      style={{ background: "#1a1a2e", border: "1px solid #252540", color: "#94a3b8" }}
                    >
                      Reset Compare
                    </button>
                  )}
                </div>
              </div>

              {/* ── COMPARE MODE: program grid for picking ── */}
              {compareMode && (comparePicking || (!compareA || !compareB)) && (
                <div>
                  {comparePicking && (
                    <div className="rounded-xl px-5 py-3 mb-4 text-sm font-medium"
                      style={{ background: "#7c3aed20", border: "1px solid #7c3aed40", color: "#a78bfa" }}>
                      Click a program to select it as Program <strong>{comparePicking}</strong>
                      {compareA && <span className="ml-3 text-xs" style={{ color: "#64748b" }}>Program A: {compareA.icon} {compareA.name}</span>}
                    </div>
                  )}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {programsList.map((prog: any) => {
                      const isA = compareA?.id === prog.id;
                      const isB = compareB?.id === prog.id;
                      return (
                        <button
                          key={prog.id}
                          onClick={() => pickForCompare(prog)}
                          disabled={isA || isB || (!comparePicking && !isA && !isB)}
                          className="rounded-2xl p-5 text-left transition-all hover:opacity-80 disabled:opacity-40"
                          style={{
                            background: isA ? "#ff6b3515" : isB ? "#7c3aed15" : "#13131f",
                            border: isA ? "2px solid #ff6b35" : isB ? "2px solid #7c3aed" : "1px solid #252540",
                          }}
                        >
                          <div className="text-2xl mb-2">{prog.icon}</div>
                          <p className="font-bold text-sm" style={{ color: "#e2e8f0" }}>{prog.name}</p>
                          <p className="text-xs" style={{ color: "#64748b" }}>{prog.subtitle}</p>
                          {isA && <p className="text-xs mt-2 font-bold" style={{ color: "#ff6b35" }}>Program A</p>}
                          {isB && <p className="text-xs mt-2 font-bold" style={{ color: "#7c3aed" }}>Program B</p>}
                          <div className="mt-3 flex gap-3 text-xs">
                            <span style={{ color: "#94a3b8" }}>{prog.enrolled_2324} enrolled</span>
                            <span style={{ color: prog.retention_2324 >= 90 ? "#10b981" : prog.retention_2324 >= 75 ? "#f59e0b" : "#ef4444" }}>
                              {prog.retention_2324}% ret.
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* ── COMPARE VIEW: side-by-side ── */}
              {compareMode && compareA && compareB && compareDetailA && compareDetailB && !comparePicking && (
                <div className="space-y-5">
                  {/* Header comparison */}
                  <div className="grid grid-cols-2 gap-5">
                    {[{ prog: compareA, detail: compareDetailA, accent: "#ff6b35" }, { prog: compareB, detail: compareDetailB, accent: "#7c3aed" }].map(({ prog, detail, accent }) => (
                      <Card key={prog.id}>
                        <div className="flex items-center gap-3 mb-4">
                          <div className="text-3xl">{prog.icon}</div>
                          <div>
                            <p className="font-bold" style={{ color: "#e2e8f0" }}>{prog.name}</p>
                            <p className="text-xs" style={{ color: "#64748b" }}>{prog.subtitle} · {prog.type}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          {[
                            { label: "Enrolled", value: detail.enrolled_2324, color: accent },
                            { label: "Completed", value: detail.completed_2324, color: "#94a3b8" },
                            { label: "Retention", value: `${detail.retention_2324}%`, color: detail.retention_2324 >= 90 ? "#10b981" : detail.retention_2324 >= 75 ? "#f59e0b" : "#ef4444" },
                          ].map((m) => (
                            <div key={m.label} className="rounded-xl p-3 text-center" style={{ background: "#0a0a14" }}>
                              <p className="text-xl font-bold" style={{ color: m.color }}>{m.value}</p>
                              <p className="text-xs mt-0.5" style={{ color: "#64748b" }}>{m.label}</p>
                            </div>
                          ))}
                        </div>
                        {detail.live_metrics && (
                          <div className="mt-3 grid grid-cols-3 gap-2">
                            {[
                              { label: "Students (live)", value: detail.live_metrics.total_students },
                              { label: "Avg Attendance", value: `${detail.live_metrics.avg_attendance?.toFixed(1)}%` },
                              { label: "At-Risk", value: detail.live_metrics.at_risk },
                            ].map((m) => (
                              <div key={m.label} className="rounded-lg p-2 text-center" style={{ background: `${accent}10`, border: `1px solid ${accent}30` }}>
                                <p className="text-base font-bold" style={{ color: accent }}>{m.value}</p>
                                <p className="text-xs" style={{ color: "#64748b" }}>{m.label}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </Card>
                    ))}
                  </div>

                  {/* Retention bar comparison */}
                  <Card>
                    <SectionTitle>Retention Rate — Head to Head</SectionTitle>
                    <div className="space-y-4">
                      {[
                        { prog: compareA, detail: compareDetailA, accent: "#ff6b35" },
                        { prog: compareB, detail: compareDetailB, accent: "#7c3aed" },
                      ].map(({ prog, detail, accent }) => (
                        <div key={prog.id}>
                          <div className="flex items-center justify-between text-sm mb-2">
                            <span style={{ color: "#e2e8f0" }}>{prog.icon} {prog.name}</span>
                            <span className="font-bold" style={{ color: detail.retention_2324 >= 90 ? "#10b981" : detail.retention_2324 >= 75 ? "#f59e0b" : "#ef4444" }}>
                              {detail.retention_2324}%
                            </span>
                          </div>
                          <div className="h-3 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                            <div
                              className="h-full rounded-full transition-all"
                              style={{ width: `${detail.retention_2324}%`, background: accent }}
                            />
                          </div>
                          <p className="text-xs mt-1" style={{ color: "#475569" }}>
                            {detail.completed_2324} of {detail.enrolled_2324} students completed
                          </p>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Attendance trend comparison */}
                  <Card>
                    <SectionTitle>Attendance Trend — Overlay</SectionTitle>
                    <div className="h-[220px] flex items-end gap-1 px-2">
                      {(() => {
                        const maxLen = Math.max(compareDetailA.trend.length, compareDetailB.trend.length);
                        return Array.from({ length: maxLen }).map((_, i) => {
                          const a = compareDetailA.trend[i]?.rate ?? 0;
                          const b = compareDetailB.trend[i]?.rate ?? 0;
                          return (
                            <div key={i} className="flex-1 flex gap-0.5 items-end">
                              <div className="flex-1 rounded-t-sm" style={{ height: `${a * 1.8}px`, background: "#ff6b35", opacity: 0.8 }} title={`${compareA.name}: ${a}%`} />
                              <div className="flex-1 rounded-t-sm" style={{ height: `${b * 1.8}px`, background: "#7c3aed", opacity: 0.8 }} title={`${compareB.name}: ${b}%`} />
                            </div>
                          );
                        });
                      })()}
                    </div>
                    <div className="flex gap-6 mt-3">
                      {[{ prog: compareA, accent: "#ff6b35" }, { prog: compareB, accent: "#7c3aed" }].map(({ prog, accent }) => (
                        <div key={prog.id} className="flex items-center gap-2 text-xs">
                          <div className="w-3 h-3 rounded-sm" style={{ background: accent }} />
                          <span style={{ color: "#94a3b8" }}>{prog.icon} {prog.name}</span>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Demographics comparison */}
                  <div className="grid grid-cols-2 gap-5">
                    {[{ prog: compareA, detail: compareDetailA, accent: "#ff6b35" }, { prog: compareB, detail: compareDetailB, accent: "#7c3aed" }].map(({ prog, detail, accent }) => (
                      <Card key={prog.id}>
                        <SectionTitle>{prog.icon} {prog.name} — Race/Ethnicity</SectionTitle>
                        <div className="space-y-2">
                          {detail.race.map((r: any) => (
                            <div key={r.label}>
                              <div className="flex justify-between text-xs mb-1">
                                <span style={{ color: "#94a3b8" }}>{r.label}</span>
                                <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{r.value}%</span>
                              </div>
                              <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                                <div className="h-full rounded-full" style={{ width: `${r.value}%`, background: accent }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* ── DRILL-DOWN: single program detail ── */}
              {!compareMode && selectedProgram && (
                <div className="space-y-5">
                  {programDetailLoading ? (
                    <div className="flex items-center justify-center py-16">
                      <p className="text-sm" style={{ color: "#64748b" }}>Loading program data…</p>
                    </div>
                  ) : programDetail ? (
                    <>
                      {/* KPIs */}
                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                        <MetricCard label="Enrolled (SY23-24)"  value={programDetail.enrolled_2324}      accent="orange" icon="📋" />
                        <MetricCard label="Completed"           value={programDetail.completed_2324}     accent="purple" icon="✅" />
                        <MetricCard label="Retention Rate"      value={`${programDetail.retention_2324}%`} accent={programDetail.retention_2324 >= 90 ? "green" : programDetail.retention_2324 >= 75 ? "yellow" : "red"} icon="📈" />
                        <MetricCard label="Enrolled (SY24-25)"  value={programDetail.enrolled_2425}      accent="green"  icon="🎓" sub={programDetail.live ? "Live data" : "Projected"} />
                      </div>

                      {/* Live metrics for 3D Game Dev */}
                      {programDetail.live_metrics && (
                        <div className="rounded-2xl px-5 py-4 flex items-center gap-6"
                          style={{ background: "#ff6b3510", border: "1px solid #ff6b3530" }}>
                          <span className="text-2xl">🎮</span>
                          <div className="flex gap-8">
                            {[
                              { label: "Live Students", value: programDetail.live_metrics.total_students },
                              { label: "Avg Attendance", value: `${programDetail.live_metrics.avg_attendance?.toFixed(1)}%` },
                              { label: "At-Risk", value: programDetail.live_metrics.at_risk, color: "#ef4444" },
                            ].map((m) => (
                              <div key={m.label}>
                                <p className="text-xl font-bold" style={{ color: (m as any).color || "#ff6b35" }}>{m.value}</p>
                                <p className="text-xs" style={{ color: "#64748b" }}>{m.label}</p>
                              </div>
                            ))}
                          </div>
                          <span className="ml-auto text-xs px-3 py-1 rounded-full font-semibold"
                            style={{ background: "#10b98120", color: "#10b981" }}>
                            ● Live Data
                          </span>
                        </div>
                      )}

                      {/* Attendance trend */}
                      <Card>
                        <SectionTitle>
                          Attendance Trend — {programDetail.live ? "Current School Year (Live)" : "SY2023-24 Historical"}
                        </SectionTitle>
                        <div className="h-[200px] flex items-end gap-1.5 px-2">
                          {programDetail.trend.map((pt: any, i: number) => {
                            const color = pt.rate >= 85 ? "#10b981" : pt.rate >= 70 ? "#f59e0b" : "#ef4444";
                            return (
                              <div key={i} className="flex-1 flex flex-col items-center group">
                                <div className="w-full rounded-t-sm transition-all group-hover:opacity-70"
                                  style={{ height: `${pt.rate * 1.8}px`, background: selectedProgram.color || "#ff6b35", opacity: 0.8 }}
                                  title={`Session ${pt.session}: ${pt.rate}%`}
                                />
                              </div>
                            );
                          })}
                        </div>
                        <div className="flex justify-between mt-2 text-xs px-1" style={{ color: "#475569" }}>
                          <span>Session 1</span>
                          <span>Session {programDetail.trend.length}</span>
                        </div>
                      </Card>

                      {/* Demographics */}
                      <div className="grid grid-cols-2 gap-5">
                        <Card>
                          <SectionTitle>Race / Ethnicity</SectionTitle>
                          <div className="space-y-3">
                            {programDetail.race.map((r: any, i: number) => {
                              const palette = ["#ff6b35", "#7c3aed", "#10b981", "#f59e0b", "#3b82f6"];
                              const clr = palette[i % palette.length];
                              return (
                                <div key={r.label}>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span style={{ color: "#94a3b8" }}>{r.label}</span>
                                    <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{r.value}%</span>
                                  </div>
                                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                                    <div className="h-full rounded-full" style={{ width: `${r.value}%`, background: clr }} />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </Card>
                        <Card>
                          <SectionTitle>Gender Identity</SectionTitle>
                          <div className="space-y-3">
                            {programDetail.gender.map((g: any, i: number) => {
                              const palette = ["#7c3aed", "#ff6b35", "#10b981"];
                              const clr = palette[i % palette.length];
                              return (
                                <div key={g.label}>
                                  <div className="flex justify-between text-xs mb-1">
                                    <span style={{ color: "#94a3b8" }}>{g.label}</span>
                                    <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{g.value}%</span>
                                  </div>
                                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                                    <div className="h-full rounded-full" style={{ width: `${g.value}%`, background: clr }} />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                          {/* Gender donut visual */}
                          <div className="mt-4 flex gap-3 flex-wrap">
                            {programDetail.gender.map((g: any, i: number) => {
                              const palette = ["#7c3aed", "#ff6b35", "#10b981"];
                              return (
                                <div key={g.label} className="flex items-center gap-1.5 text-xs">
                                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: palette[i % 3] }} />
                                  <span style={{ color: "#64748b" }}>{g.label}: <strong style={{ color: "#e2e8f0" }}>{g.value}%</strong></span>
                                </div>
                              );
                            })}
                          </div>
                        </Card>
                      </div>

                      {/* Context note */}
                      {!programDetail.live && (
                        <div className="rounded-xl px-5 py-3 text-xs" style={{ background: "#1a1a2e", border: "1px solid #252540", color: "#64748b" }}>
                          ℹ️ Attendance trend is synthetically generated from SY2023-24 retention baseline. Demographics reflect program-wide proportions from Urban Arts SY2023-24 actuals.
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              )}

              {/* ── DEFAULT: program card grid ── */}
              {!selectedProgram && !compareMode && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {programsList.map((prog: any) => {
                    const retColor = prog.retention_2324 >= 90 ? "#10b981" : prog.retention_2324 >= 75 ? "#f59e0b" : "#ef4444";
                    return (
                      <button
                        key={prog.id}
                        onClick={() => openProgram(prog)}
                        className="rounded-2xl p-5 text-left transition-all hover:scale-[1.02] hover:opacity-90"
                        style={{ background: "#13131f", border: "1px solid #252540" }}
                      >
                        <div className="text-3xl mb-3">{prog.icon}</div>
                        <p className="font-bold text-base" style={{ color: "#e2e8f0" }}>{prog.name}</p>
                        <p className="text-xs mb-4" style={{ color: "#64748b" }}>{prog.subtitle} · {prog.type}</p>

                        <div className="grid grid-cols-2 gap-2 mb-3">
                          <div className="rounded-lg p-2" style={{ background: "#0a0a14" }}>
                            <p className="text-lg font-bold" style={{ color: prog.color }}>{prog.enrolled_2324}</p>
                            <p className="text-xs" style={{ color: "#475569" }}>Enrolled</p>
                          </div>
                          <div className="rounded-lg p-2" style={{ background: "#0a0a14" }}>
                            <p className="text-lg font-bold" style={{ color: retColor }}>{prog.retention_2324}%</p>
                            <p className="text-xs" style={{ color: "#475569" }}>Retention</p>
                          </div>
                        </div>

                        {/* Retention bar */}
                        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a2e" }}>
                          <div className="h-full rounded-full" style={{ width: `${prog.retention_2324}%`, background: retColor }} />
                        </div>

                        {prog.live && (
                          <span className="mt-3 inline-block text-xs px-2 py-0.5 rounded-full font-semibold"
                            style={{ background: "#10b98120", color: "#10b981" }}>
                            ● Live
                          </span>
                        )}

                        <p className="mt-3 text-xs" style={{ color: "#475569" }}>
                          Click to drill down →
                        </p>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

        </div>
      </main>

      {/* ── Floating Chat Button ─────────────────────────────────────────── */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-2xl flex items-center justify-center text-2xl shadow-2xl transition-all hover:scale-105 hover:opacity-90 z-40"
          style={{
            background: "linear-gradient(135deg, #ff6b35, #7c3aed)",
            boxShadow: "0 8px 32px rgba(124,58,237,0.4)",
          }}
          title="AI Chat Assistant"
        >
          🤖
        </button>
      )}

      {/* ── Chat Panel ──────────────────────────────────────────────────── */}
      {chatOpen && <ChatPanel onClose={() => setChatOpen(false)} />}
    </div>
  );
}
