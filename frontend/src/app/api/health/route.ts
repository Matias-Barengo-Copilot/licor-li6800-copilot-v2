import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET() {
  let studentCount = 0;
  try {
    const { rows } = await pool.query<{ count: string }>(
      "SELECT COUNT(*) FROM students"
    );
    studentCount = Number(rows[0]?.count) || 0;
  } catch {
    // DB unavailable — still return ok
  }
  return NextResponse.json({ status: "ok", students: studentCount });
}
