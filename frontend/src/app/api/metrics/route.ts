import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows, getSessionTrendRows } from "@/lib/db";
import { overviewMetrics } from "@/lib/analytics";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const [att, session] = await Promise.all([
      getAttendanceRows(),
      getSessionTrendRows(),
    ]);
    return NextResponse.json(overviewMetrics(att, session));
  } catch (err) {
    console.error("GET /api/metrics:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
