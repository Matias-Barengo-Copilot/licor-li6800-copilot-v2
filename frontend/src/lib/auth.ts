import jwt from "jsonwebtoken";
import { NextRequest, NextResponse } from "next/server";

const JWT_SECRET = process.env.JWT_SECRET!;
const COOKIE_NAME = "token";

export interface JwtPayload {
  user_id: string | number;
  email: string;
  role: string;
  exp?: number;
}

export function verifyToken(token: string): JwtPayload | null {
  try {
    return jwt.verify(token, JWT_SECRET) as JwtPayload;
  } catch {
    return null;
  }
}

export function signToken(payload: Omit<JwtPayload, "exp">): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: "8h" });
}

export function setAuthCookie(res: NextResponse, token: string): void {
  res.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 8 * 60 * 60,
  });
}

/** Extract and verify token from request (Bearer header first, then cookie). */
export function getAuthUser(req: NextRequest): JwtPayload | null {
  const authHeader = req.headers.get("authorization");
  if (authHeader?.startsWith("Bearer ")) {
    return verifyToken(authHeader.slice(7));
  }
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (token) return verifyToken(token);
  return null;
}

/** Returns 401 response if not authenticated. */
export function requireAuth(
  req: NextRequest
): { user: JwtPayload } | NextResponse {
  const user = getAuthUser(req);
  if (!user) {
    return NextResponse.json(
      { error: "Authentication required" },
      { status: 401 }
    );
  }
  return { user };
}
