import { NextResponse } from "next/server";

/**
 * Bootstrap probe used by M0 to prove that a cookie set by the frontend is
 * first-party through Caddy. Replaced by the real session routes in M7.
 */
export function GET() {
  const response = NextResponse.json({ ok: true, surface: "frontend" });
  response.cookies.set("sb_boot", "1", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60,
  });
  return response;
}