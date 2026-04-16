import { NextRequest, NextResponse } from "next/server";
import bcrypt from "bcryptjs";
import { signToken, setAuthCookie } from "@/lib/auth";
import { getUserByEmail } from "@/lib/db";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const email = (body.email ?? "").trim().toLowerCase();
    const password = (body.password ?? "").trim();

    const user = await getUserByEmail(email);
    if (!user || !(await bcrypt.compare(password, user.password_hash))) {
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
    }

    const token = signToken({
      user_id: String(user.id),
      email: user.email,
      role: user.role,
    });

    const res = NextResponse.json({
      ok: true,
      user: {
        id: String(user.id),
        email: user.email,
        role: user.role,
        name: user.name,
      },
    });
    setAuthCookie(res, token);
    return res;
  } catch (err) {
    console.error("POST /api/auth/login:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
