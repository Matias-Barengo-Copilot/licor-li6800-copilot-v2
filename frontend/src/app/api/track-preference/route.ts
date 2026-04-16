import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { artVsProgramming } from "@/lib/analytics";
import { loadWork } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const work = loadWork();
    return NextResponse.json(artVsProgramming(work));
  } catch (err) {
    console.error("GET /api/track-preference:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
