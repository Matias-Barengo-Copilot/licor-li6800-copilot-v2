import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getProgramAttendanceRates } from "@/lib/db";
import { loadDemographicsSummary } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const demo = loadDemographicsSummary();

    // Replace hardcoded attendance_rates with real DB data
    try {
      const realRates = await getProgramAttendanceRates();
      if (realRates.length > 0) {
        demo.attendance_rates = realRates.map((r) => ({
          program: r.program,
          rate_2324: null,
          rate_2425: r.rate,
        }));
      }
    } catch {
      // keep hardcoded fallback if DB fails
    }

    return NextResponse.json(demo);
  } catch (err) {
    console.error("GET /api/demographics:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
