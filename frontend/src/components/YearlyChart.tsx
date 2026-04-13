"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  Program: string;
  Year: string;
  Enrolled: number;
}

const COLORS = ["#ff6b35", "#7c3aed", "#10b981", "#f59e0b", "#3b82f6", "#ec4899", "#06b6d4"];

function Tip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl p-3 text-sm" style={{ background: "#1a1a2e", border: "1px solid #252540" }}>
      <p className="font-semibold mb-1" style={{ color: "#e2e8f0" }}>{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <b>{p.value}</b></p>
      ))}
    </div>
  );
}

export default function YearlyChart({ data }: { data: DataPoint[] }) {
  // Pivot: year -> {program: value}
  const years = [...new Set(data.map((d) => d.Year))].sort();
  const programs = [...new Set(data.map((d) => d.Program))];

  const pivoted = years.map((yr) => {
    const row: any = { year: yr };
    programs.forEach((prog) => {
      const match = data.find((d) => d.Year === yr && d.Program === prog);
      row[prog] = match?.Enrolled ?? null;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={pivoted} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
        <XAxis dataKey="year" tick={{ fill: "#64748b", fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip content={<Tip />} />
        <Legend wrapperStyle={{ color: "#64748b", fontSize: 11 }} />
        {programs.map((prog, i) => (
          <Line
            key={prog}
            type="monotone"
            dataKey={prog}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={{ r: 4, fill: COLORS[i % COLORS.length], strokeWidth: 0 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
