import { NextRequest, NextResponse } from "next/server";

import { backendUrl } from "@/lib/api";
import { guardOrigin, problem } from "@/lib/http";

type Context = { params: Promise<{ path: string[] }> };

const ALLOWED = new Set([
  "password-reset/request",
  "password-reset/confirm",
  "verify-email/confirm",
]);

async function handle(request: NextRequest, context: Context) {
  const originError = guardOrigin(request);
  if (originError) return originError;

  const { path } = await context.params;
  const target = path?.join("/") ?? "";
  if (!ALLOWED.has(target)) {
    return problem(404, "not_found", "Alamat tidak ditemukan");
  }

  const body = await request.text();
  let response: Response;
  try {
    response = await fetch(backendUrl(`/auth/${target}`), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
      cache: "no-store",
    });
  } catch {
    return problem(
      503,
      "api_unavailable",
      "Layanan sedang tidak tersedia",
      "Coba lagi beberapa saat lagi.",
    );
  }

  const text = await response.text();
  return new NextResponse(text, {
    status: response.status,
    headers: {
      "content-type":
        response.headers.get("content-type") ?? "application/json",
      ...(response.headers.get("retry-after")
        ? { "retry-after": response.headers.get("retry-after") as string }
        : {}),
    },
  });
}

export async function POST(request: NextRequest, context: Context) {
  return handle(request, context);
}

export const dynamic = "force-dynamic";