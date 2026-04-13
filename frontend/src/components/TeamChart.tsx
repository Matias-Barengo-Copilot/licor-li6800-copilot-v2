"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface Team {
  "Project Team Name": string;
  Students: number;
  Avg_Attendance: number;
  Avg_Good: number;
  Avg_Missing: number;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded-xl p-3 text-sm"
      style={{ background: "#1a1a2e", border: "1px solid #252540" }}
    >
      <p className="font-semibold mb-2" style={{ color: "#e2e8f0" }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <b>{p.value?.toFixed(1)}%</b>
        </p>
      ))}
    </div>
  );
}

export default function TeamChart({ teams }: { teams: Team[] }) {
  const data = teams.map((t) => ({
    name: t["Project Team Name"],
    "Attendance %": t.Avg_Attendance,
    "Work Quality %": t.Avg_Good,
    "Missing %": t.Avg_Missing,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }} barGap={4}>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
        <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis domain={[0, 110]} tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
        <Tooltip content={<CustomTooltip />} />
        <Legend wrapperStyle={{ color: "#64748b", fontSize: 12 }} />
        <Bar dataKey="Attendance %" fill="#ff6b35" radius={[4, 4, 0, 0]} />
        <Bar dataKey="Work Quality %" fill="#7c3aed" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
