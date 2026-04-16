import { NextRequest, NextResponse } from "next/server";
import { requireAuth } from "@/lib/auth";
import { getAttendanceRows } from "@/lib/db";
import { studentPerformanceTable } from "@/lib/analytics";
import { loadWork } from "@/lib/data-loader";

export async function GET(req: NextRequest) {
  const auth = requireAuth(req);
  if (auth instanceof NextResponse) return auth;

  try {
    const { searchParams } = req.nextUrl;
    const minAtt = parseFloat(searchParams.get("min_att") ?? "0");
    const maxAtt = parseFloat(searchParams.get("max_att") ?? "100");
    const team = searchParams.get("team") ?? "All";
    const sort = searchParams.get("sort") ?? "attendance_desc";

    const [att, work] = await Promise.all([getAttendanceRows(), Promise.resolve(loadWork())]);
    let perf = studentPerformanceTable(att, work);

    // Filter
    perf = perf.filter(
      (r) => r["Attendance %"] >= minAtt && r["Attendance %"] <= maxAtt
    );
    if (team !== "All") {
      perf = perf.filter((r) => r["Project Team Name"] === team);
    }

    // Sort
    const sortMap: Record<string, [keyof (typeof perf)[0], boolean]> = {
      attendance_desc: ["Attendance %", false],
      attendance_asc:  ["Attendance %", true],
      absences_desc:   ["Absent", false],
      missing_desc:    ["% missing_num", false],
    };
    const [col, asc] = sortMap[sort] ?? sortMap.attendance_desc;
    perf = perf.sort((a, b) => {
      const va = (a[col] as number) ?? 0;
      const vb = (b[col] as number) ?? 0;
      return asc ? va - vb : vb - va;
    });

    return NextResponse.json(perf);
  } catch (err) {
    console.error("GET /api/students:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
