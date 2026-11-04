import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/api";
import { guardOrigin, problem } from "@/lib/http";
import { createOpsSession, destroyOpsSession, readOpsSession } from "@/lib/ops-session";

type LoginBody = { email?: string; password?: string };

type TokenPayload = {
  user: { id: string; email: string };
  access_token: string;
  refresh_token: string;
  scope: string;
};

export async function POST(request: Request) {
  const originError = guardOrigin(request);
  if (originError) return originError;

  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return problem(400, "invalid_json", "Body harus berupa JSON");
  }

  const email = body.email?.trim();
  const password = body.password ?? "";
  if (!email || !password) {
    return problem(422, "invalid_credentials_shape", "Lengkapi email dan kata sandi");
  }

  let response: Response;
  try {
    response = await fetch(backendUrl("/auth/platform-login"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email, password }),
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

  if (!response.ok) {
    const text = await response.text();
    return new NextResponse(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json",
        ...(response.headers.get("retry-after")
          ? { "retry-after": response.headers.get("retry-after") as string }
          : {}),
      },
    });
  }

  const payload = (await response.json()) as TokenPayload;
  if (payload.scope !== "platform") {
    return problem(403, "platform_required", "Akun ini bukan operator platform");
  }

  const created = await createOpsSession({
    user_id: payload.user.id,
    email: payload.user.email,
    access_token: payload.access_token,
    refresh_token: payload.refresh_token,
    created_at: new Date().toISOString(),
  });
  if (!created) {
    return problem(
      503,
      "session_store_unavailable",
      "Sesi tidak dapat disimpan",
      "Penyimpanan sesi sedang tidak tersedia. Coba lagi.",
    );
  }

  return NextResponse.json({ ok: true });
}

export async function DELETE(request: Request) {
  const originError = guardOrigin(request);
  if (originError) return originError;

  const session = await readOpsSession();
  if (session) {
    try {
      await fetch(backendUrl("/auth/logout"), {
        method: "POST",
        headers: {
          authorization: `Bearer ${session.data.access_token}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({ all_sessions: true }),
        cache: "no-store",
      });
    } catch {
      // Local session removal still matters when the API is unreachable.
    }
    await destroyOpsSession(session.sid);
  } else {
    await destroyOpsSession();
  }
  return new NextResponse(null, { status: 204 });
}