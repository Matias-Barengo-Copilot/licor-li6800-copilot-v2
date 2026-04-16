import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows } from "@/lib/db";
import { studentPerformanceTable } from "@/lib/analytics";
import { loadWork } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const [att, work] = await Promise.all([getAttendanceRows(), Promise.resolve(loadWork())]);
    const perf = studentPerformanceTable(att, work);
    const teams = [
      ...new Set(
        perf
          .map((r) => r["Project Team Name"])
          .filter((t): t is string => t != null && t !== "")
      ),
    ].sort();
    return NextResponse.json(teams);
  } catch (err) {
    console.error("GET /api/teams-list:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
