"use client";

interface MetricCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "orange" | "green" | "red" | "purple" | "yellow";
  icon?: React.ReactNode;
}

const accentMap = {
  orange: "#ff6b35",
  green: "#10b981",
  red: "#ef4444",
  purple: "#7c3aed",
  yellow: "#f59e0b",
};

export default function MetricCard({ label, value, sub, accent = "orange", icon }: MetricCardProps) {
  const color = accentMap[accent];
  return (
    <div
      className="relative rounded-2xl p-5 overflow-hidden group transition-all duration-200 hover:-translate-y-0.5"
      style={{
        background: "linear-gradient(135deg, #13131f 0%, #1a1a2e 100%)",
        border: "1px solid #252540",
        boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
      }}
    >
      {/* Accent glow */}
      <div
        className="absolute top-0 right-0 w-24 h-24 rounded-full blur-3xl opacity-10 group-hover:opacity-20 transition-opacity"
        style={{ background: color }}
      />

      <div className="flex items-start justify-between relative">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#64748b" }}>
            {label}
          </p>
          <p className="text-3xl font-bold tracking-tight" style={{ color: "#e2e8f0" }}>
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
