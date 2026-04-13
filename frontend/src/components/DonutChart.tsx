"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface Slice {
  name: string;
  value: number;
}

const PALETTE = [
  "#ff6b35", "#7c3aed", "#10b981", "#f59e0b",
  "#3b82f6", "#ec4899", "#06b6d4", "#84cc16", "#f97316",
];

function Tip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="rounded-xl p-3 text-sm" style={{ background: "#1a1a2e", border: "1px solid #252540" }}>
      <p className="font-semibold" style={{ color: "#e2e8f0" }}>{d.name}</p>
      <p style={{ color: d.payload.fill }}>{d.value}% · {d.payload.n} students</p>
    </div>
  );
}

interface Props {
  data: { category: string; pct_2425: number; n_2425: number }[];
  title?: string;
  height?: number;
}

export default function DonutChart({ data, title, height = 240 }: Props) {
  const slices = data
    .filter((d) => d.pct_2425 > 0)
    .map((d, i) => ({
      name: d.category,
      value: d.pct_2425,
      n: d.n_2425,
      fill: PALETTE[i % PALETTE.length],
    }));

  return (
    <div>
      {title && (
        <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#64748b" }}>
          {title}
        </p>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={slices}
            cx="50%"
            cy="45%"
            innerRadius={height * 0.22}
            outerRadius={height * 0.36}
            paddingAngle={2}
            dataKey="value"
          >
            {slices.map((s, i) => (
              <Cell key={i} fill={s.fill} stroke="none" />
            ))}
          </Pie>
          <Tooltip content={<Tip />} />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(v) => <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>}
            wrapperStyle={{ paddingTop: 8 }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
