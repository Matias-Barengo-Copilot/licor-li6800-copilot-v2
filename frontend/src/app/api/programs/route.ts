import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getPrograms } from "@/lib/db";
import { formatProgram } from "@/lib/format-program";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const programs = await getPrograms();
    return NextResponse.json(programs.map(formatProgram));
  } catch (err) {
    console.error("GET /api/programs:", err);
    return NextResponse.json([], { status: 200 }); // graceful fallback
  }
}
