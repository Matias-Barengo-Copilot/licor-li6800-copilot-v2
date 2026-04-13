"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";

interface SessionData {
  date: string;
  attendance_rate: number;
  present: number;
  absent: number;
  late: number;
}

interface Props {
  data: SessionData[];
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded-xl p-3 text-sm"
      style={{
        background: "#1a1a2e",
        border: "1px solid #252540",
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      }}
    >
      <p className="font-semibold mb-2" style={{ color: "#e2e8f0" }}>
        {new Date(label).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
      </p>
      <p style={{ color: "#ff6b35" }}>
        Attendance: <b>{d.attendance_rate}%</b>
      </p>
      <p style={{ color: "#10b981" }}>Present: {d.present}</p>
      <p style={{ color: "#f59e0b" }}>Late: {d.late}</p>
      <p style={{ color: "#ef4444" }}>Absent: {d.absent}</p>
    </div>
  );
}

export default function AttendanceChart({ data }: Props) {
  const formatted = data.map((d) => ({
    ...d,
    label: new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={formatted} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id="attGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ff6b35" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ff6b35" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#252540" />
        <XAxis
          dataKey="label"
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fill: "#64748b", fontSize: 10 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={80}
          stroke="#f59e0b"
          strokeDasharray="4 4"
          label={{ value: "80% target", fill: "#f59e0b", fontSize: 10, position: "insideTopRight" }}
        />
        <Area
          type="monotone"
          dataKey="attendance_rate"
          stroke="#ff6b35"
          strokeWidth={2.5}
          fill="url(#attGrad)"
          dot={false}
          activeDot={{ r: 5, fill: "#ff6b35", strokeWidth: 0 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
