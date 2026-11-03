import { NextResponse } from "next/server";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { code: "invalid_json", message: "Body harus berupa JSON." },
      { status: 400 },
    );
  }

  const forwardedFor =
    request.headers.get("x-forwarded-for") ??
    request.headers.get("x-real-ip") ??
    "unknown";
  const userAgent = request.headers.get("user-agent") ?? "";

  try {
    const upstream = await fetch(`${API_BASE_URL}/api/v1/leads`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "x-forwarded-for": forwardedFor,
        "user-agent": userAgent,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "content-type":
          upstream.headers.get("content-type") ?? "application/json",
        ...(upstream.headers.get("retry-after")
          ? { "retry-after": upstream.headers.get("retry-after") as string }
          : {}),
      },
    });
  } catch {
    return NextResponse.json(
      {
        code: "upstream_unavailable",
        message: "Layanan demo sedang tidak tersedia. Coba lagi sesaat.",
      },
      { status: 503 },
    );
  }
}