import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import {
  getProgramById,
  getSessionTrendForProgram,
  getAtRiskForProgram,
} from "@/lib/db";
import { formatProgram } from "@/lib/format-program";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ program_id: string }> }
) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const { program_id } = await params;

    const raw = await getProgramById(program_id);
    if (!raw) {
      return NextResponse.json(
        { detail: "Program not found" },
        { status: 404 }
      );
    }

    const prog = formatProgram(raw);
    const trend = await getSessionTrendForProgram(program_id);

    let liveMetrics = null;
    if (prog.live) {
      liveMetrics = {
        total_students: raw.enrolled,
        avg_attendance: raw.attendance_rate,
        at_risk: await getAtRiskForProgram(program_id),
      };
    }

    return NextResponse.json({
      ...prog,
      live_metrics: liveMetrics,
      trend,
      race: [],
      gender: [],
    });
  } catch (err) {
    console.error("GET /api/program:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
