import { NextResponse } from "next/server";

import { refreshTokens } from "@/lib/api";
import { guardOrigin, problem } from "@/lib/http";
import { destroySession, readSession } from "@/lib/session";

export async function POST(request: Request) {
  const originError = guardOrigin(request);
  if (originError) return originError;

  const session = await readSession();
  if (!session) {
    return problem(401, "session_required", "Sesi tidak ditemukan");
  }

  const refreshed = await refreshTokens(session);
  if (!refreshed) {
    await destroySession(session.sid);
    return problem(401, "session_expired", "Sesi berakhir, silakan masuk lagi");
  }

  return new NextResponse(null, { status: 204 });
}