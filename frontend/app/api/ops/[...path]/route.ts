import { NextRequest } from "next/server";

import { guardOrigin, problem, proxyResponse } from "@/lib/http";
import { requireOpsSessionForRoute } from "@/lib/ops-http";
import { OpsSessionExpiredError, opsApiResponse } from "@/lib/ops-api";
import { destroyOpsSession } from "@/lib/ops-session";

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context) {
  const method = request.method.toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    const originError = guardOrigin(request);
    if (originError) return originError;
  }

  const { session, response } = await requireOpsSessionForRoute();
  if (!session) return response;

  const { path } = await context.params;
  if (
    !path?.length ||
    path.some(
      (segment) =>
        !/^[A-Za-z0-9._-]+$/.test(segment) ||
        segment === "." ||
        segment === "..",
    )
  ) {
    return problem(400, "invalid_path", "Alamat API tidak valid");
  }

  const target = `/${path.join("/")}${request.nextUrl.search}`;
  const body =
    method === "GET" || method === "HEAD" ? null : await request.text();
  const headers: Record<string, string> = {};
  const contentType = request.headers.get("content-type");
  if (contentType && body !== null) headers["content-type"] = contentType;

  try {
    const upstream = await opsApiResponse(session, target, {
      method,
      body,
      headers,
    });
    return proxyResponse(upstream);
  } catch (error) {
    if (error instanceof OpsSessionExpiredError) {
      await destroyOpsSession(session.sid);
      return problem(401, "session_expired", "Sesi operator berakhir");
    }
    return problem(503, "api_unavailable", "Layanan sedang tidak tersedia");
  }
}

export async function GET(request: NextRequest, context: Context) {
  return handle(request, context);
}

export async function POST(request: NextRequest, context: Context) {
  return handle(request, context);
}

export async function PATCH(request: NextRequest, context: Context) {
  return handle(request, context);
}

export async function DELETE(request: NextRequest, context: Context) {
  return handle(request, context);
}

export async function PUT(request: NextRequest, context: Context) {
  return handle(request, context);
}

export async function HEAD(request: NextRequest, context: Context) {
  return handle(request, context);
}

export const dynamic = "force-dynamic";