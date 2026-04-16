import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows } from "@/lib/db";
import { lateVsAbsentCorrelation } from "@/lib/analytics";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const att = await getAttendanceRows();
    return NextResponse.json(lateVsAbsentCorrelation(att));
  } catch (err) {
    console.error("GET /api/late-absent-correlation:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
