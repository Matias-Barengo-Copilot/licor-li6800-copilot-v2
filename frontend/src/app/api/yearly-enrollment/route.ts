import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { yearlyEnrollmentTrend } from "@/lib/analytics";
import { loadYearly } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const enroll = loadYearly();
    return NextResponse.json(yearlyEnrollmentTrend(enroll));
  } catch (err) {
    console.error("GET /api/yearly-enrollment:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
