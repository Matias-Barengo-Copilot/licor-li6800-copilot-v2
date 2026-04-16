"use client";

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "orange" | "green" | "red" | "purple" | "yellow";
  icon?: React.ReactNode;
}

const accentMap = {
  orange: "#c6f000",
  green: "#c6f000",
  red: "#ef4444",
  purple: "#0b1b2b",
  yellow: "#f59e0b",
};

export default function MetricCard({ label, value, sub, accent = "orange", icon }: MetricCardProps) {
  const color = accentMap[accent];
  return (
    <div
      className="relative rounded-xl p-5 overflow-hidden group transition-all duration-300 hover:-translate-y-0.5"
      style={{
        background: "#ffffff",
        border: "1px solid #ededed",
        boxShadow: "0 2px 10px rgba(11,27,43,0.08)",
      }}
    >
      {/* Accent glow */}
      <div
        className="absolute top-0 right-0 w-20 h-20 rounded-full blur-3xl opacity-10 group-hover:opacity-15 transition-opacity"
        style={{ background: color }}
      />

      <div className="flex items-start justify-between relative">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#475569" }}>
            {label}
          </p>
          <p className="text-3xl font-bold tracking-tight" style={{ color: "#0b1b2b" }}>
            {value}
          </p>
          {sub && (
            <p className="text-xs mt-1.5" style={{ color: color }}>
              {sub}
            </p>
          )}
        </div>
        {icon && (
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-xl"
            style={{ background: `${color}20`, color }}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Bottom accent line */}
      <div
        className="absolute bottom-0 left-0 right-0 h-0.5 opacity-40"
        style={{ background: `linear-gradient(90deg, ${color}, transparent)` }}
      />
    </div>
  );
}
