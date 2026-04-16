"use client";

import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Invalid credentials");
        return;
      }

      // Server has set the httpOnly cookie — navigate to dashboard
      window.location.href = "/";
    } catch {
      setError("Network error — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "#0b1b2b" }}>
      <div
        className="w-full max-w-sm p-8 rounded-2xl"
        style={{ background: "#111f2e", border: "1px solid #1e3048" }}
      >
        <h1 className="text-2xl font-bold text-white mb-1">Program IQ</h1>
        <p className="text-sm mb-6" style={{ color: "#64748b" }}>Urban Arts Intelligence Dashboard</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm mb-1" style={{ color: "#94a3b8" }}>Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
              className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
              style={{
                background: "#0b1b2b",
                border: "1px solid #1e3048",
                color: "#ffffff",
              }}
            />
          </div>

          <div>
            <label className="block text-sm mb-1" style={{ color: "#94a3b8" }}>Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
              style={{
                background: "#0b1b2b",
                border: "1px solid #1e3048",
                color: "#ffffff",
              }}
            />
          </div>

          {error && (
            <p className="text-sm" style={{ color: "#f87171" }}>{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg font-medium text-sm transition-opacity disabled:opacity-50"
            style={{ background: "#c6f000", color: "#0b1b2b" }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
