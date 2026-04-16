import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows } from "@/lib/db";
import { studentPerformanceTable, teamPerformance } from "@/lib/analytics";
import { loadWork } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const [att, work] = await Promise.all([getAttendanceRows(), Promise.resolve(loadWork())]);
    const perf = studentPerformanceTable(att, work);
    return NextResponse.json(teamPerformance(perf));
  } catch (err) {
    console.error("GET /api/teams:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
