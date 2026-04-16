import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows } from "@/lib/db";
import { attendanceDistribution } from "@/lib/analytics";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const att = await getAttendanceRows();
    return NextResponse.json(attendanceDistribution(att));
  } catch (err) {
    console.error("GET /api/attendance-distribution:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
