"use client";

import {
  PieChart, Pie, Cell, Tooltip as PieTip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as BarTip,
  LineChart, Line, ResponsiveContainer, Legend,
} from "recharts";
import type { ChartData } from "@/lib/api";

const PALETTE = [
  "#ff6b35", "#7c3aed", "#10b981", "#f59e0b",
  "#3b82f6", "#ec4899", "#06b6d4", "#84cc16",
  "#f97316", "#a855f7",
];

const DARK = { background: "#0f0f1a", border: "1px solid #252540", color: "#e2e8f0", fontSize: 11 };

function Tip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{ background: "#1a1a2e", border: "1px solid #252540", borderRadius: 8, padding: "8px 12px", fontSize: 12 }}>
      <p style={{ color: "#e2e8f0", fontWeight: 600 }}>{d.payload.label ?? d.name}</p>
      <p style={{ color: d.color ?? d.fill ?? "#ff6b35" }}>{d.value}{d.payload.unit ?? ""}</p>
    </div>
  );
}

export default function InlineChart({ chart }: { chart: ChartData }) {
  const { chart_type, title, data, unit = "%", insight } = chart;

  const enriched = data.map((d, i) => ({
    ...d,
    fill: PALETTE[i % PALETTE.length],
    unit,
  }));

  const isPie = chart_type === "pie" || chart_type === "donut";
  const isHorizontal = chart_type === "horizontal_bar";
  const isLine = chart_type === "line";

  return (
    <div
      className="mt-2 rounded-2xl overflow-hidden"
      style={{ background: "#0f0f1a", border: "1px solid #252540", padding: "16px" }}
    >
      <p className="text-xs font-semibold mb-3" style={{ color: "#94a3b8" }}>{title}</p>

      <ResponsiveContainer width="100%" height={200}>
        {isPie ? (
          <PieChart>
            <Pie
              data={enriched}
              dataKey="value"
              nameKey="label"
              cx="50%"
              cy="50%"
              innerRadius={chart_type === "donut" ? 40 : 0}
              outerRadius={75}
              paddingAngle={2}
              label={({ name, value }: any) => `${name} ${value}${unit}`}
              labelLine={false}
            >
              {enriched.map((d, i) => (
                <Cell key={i} fill={d.fill} stroke="none" />
              ))}
            </Pie>
            <PieTip content={<Tip />} />
          </PieChart>
        ) : isHorizontal ? (
          <BarChart data={enriched} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
            <XAxis type="number" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false}
              tickFormatter={(v) => `${v}${unit}`} />
            <YAxis type="category" dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} tickLine={false} axisLine={false} width={110} />
            <BarTip content={<Tip />} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {enriched.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        ) : isLine ? (
          <LineChart data={enriched} margin={{ left: 0, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
            <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false}
              tickFormatter={(v) => `${v}${unit}`} />
            <BarTip content={<Tip />} />
            <Line type="monotone" dataKey="value" stroke="#ff6b35" strokeWidth={2}
              dot={{ r: 4, fill: "#ff6b35", strokeWidth: 0 }} />
          </LineChart>
        ) : (
          /* default: vertical bar */
          <BarChart data={enriched} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
            <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} tickLine={false} axisLine={false}
              tickFormatter={(v) => `${v}${unit}`} />
            <BarTip content={<Tip />} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {enriched.map((d, i) => <Cell key={i} fill={d.fill} />)}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>

      {insight && (
        <p className="mt-3 text-xs" style={{ color: "#64748b", borderTop: "1px solid #1a1a2e", paddingTop: 8 }}>
          💡 {insight}
        </p>
      )}
    </div>
  );
}
