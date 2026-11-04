import "server-only";

import { NextResponse } from "next/server";

import { destroySession, readSession } from "@/lib/session";

export function sameOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;
  const allowed = new Set<string>();
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  if (configured) allowed.add(configured.replace(/\/$/, ""));
  try {
    allowed.add(new URL(request.url).origin);
  } catch {
    // Ignore malformed request URLs.
  }
  return allowed.has(origin.replace(/\/$/, ""));
}

export function problem(
  status: number,
  code: string,
  title: string,
  detail?: string,
): NextResponse {
  return NextResponse.json(
    { type: `https://sehatbridge.dev/errors/${code}`, title, status, code, detail },
    { status },
  );
}

export async function proxyResponse(response: Response): Promise<NextResponse> {
  const body = await response.arrayBuffer();
  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const retryAfter = response.headers.get("retry-after");
  if (retryAfter) headers.set("retry-after", retryAfter);
  return new NextResponse(body.byteLength ? body : null, {
    status: response.status,
    headers,
  });
}

export async function requireSessionForRoute() {
  const session = await readSession();
  if (!session) {
    return { session: null, response: problem(401, "session_required", "Sesi tidak ditemukan") };
  }
  return { session, response: null };
}

export async function clearExpiredSession(sid?: string) {
  await destroySession(sid);
}

export function guardOrigin(request: Request): NextResponse | null {
  if (sameOrigin(request)) return null;
  return problem(403, "origin_mismatch", "Asal permintaan tidak diizinkan");
}