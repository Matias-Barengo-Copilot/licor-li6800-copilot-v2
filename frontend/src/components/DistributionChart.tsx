"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from "recharts";

const COLORS: Record<string, string> = {
  "<60%": "#ef4444",
  "60–70%": "#f97316",
  "70–80%": "#f59e0b",
  "80–90%": "#84cc16",
  "90–100%": "#10b981",
};

function Tip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl p-3 text-sm" style={{ background: "#1a1a2e", border: "1px solid #252540" }}>
      <p style={{ color: "#e2e8f0" }}>{payload[0].payload["Attendance Band"]}</p>
      <p style={{ color: payload[0].fill }}><b>{payload[0].value} students</b></p>
    </div>
  );
}

export default function DistributionChart({ data }: { data: { "Attendance Band": string; Students: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
        <XAxis dataKey="Attendance Band" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
        <Tooltip content={<Tip />} />
        <Bar dataKey="Students" radius={[6, 6, 0, 0]}>
          {data.map((entry) => (
            <Cell key={entry["Attendance Band"]} fill={COLORS[entry["Attendance Band"]] || "#ff6b35"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
