import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getSessionTrendRows } from "@/lib/db";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const rows = await getSessionTrendRows();
    return NextResponse.json(rows);
  } catch (err) {
    console.error("GET /api/session-trend:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
