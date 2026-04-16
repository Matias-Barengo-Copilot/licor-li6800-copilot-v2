import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceLongRows } from "@/lib/db";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ student_id: string }> }
) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const { student_id } = await params;
    const all = await getAttendanceLongRows();
    const filtered = all
      .filter((r) => r.student_id === student_id)
      .map((r) => ({
        session_date: r.session_date,
        attendance_status: r.attendance_status,
      }));
    return NextResponse.json(filtered);
  } catch (err) {
    console.error("GET /api/student-sessions:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
