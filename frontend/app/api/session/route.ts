import "server-only";

import { NextResponse } from "next/server";

import { backendUrl } from "@/lib/api";
import { guardOrigin, problem } from "@/lib/http";
import { createSession, destroySession, readSession } from "@/lib/session";

type LoginBody = {
  tenant_slug?: string;
  email?: string;
  password?: string;
};

type TokenPayload = {
  access_token: string;
  refresh_token: string;
};

type MePayload = {
  id: string;
  email: string;
  is_platform_admin: boolean;
  membership: {
    role: "owner" | "admin" | "member";
    tenant: { id: string; slug: string; name: string };
  } | null;
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

  const tenantSlug = body.tenant_slug?.trim().toLowerCase();
  const email = body.email?.trim();
  const password = body.password ?? "";
  if (!tenantSlug || !email || !password) {
    return problem(422, "invalid_credentials_shape", "Lengkapi semua kolom");
  }

  let loginResponse: Response;
  try {
    loginResponse = await fetch(backendUrl("/auth/login"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ tenant_slug: tenantSlug, email, password }),
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

  if (!loginResponse.ok) {
    const text = await loginResponse.text();
    return new NextResponse(text, {
      status: loginResponse.status,
      headers: {
        "content-type":
          loginResponse.headers.get("content-type") ?? "application/json",
        ...(loginResponse.headers.get("retry-after")
          ? { "retry-after": loginResponse.headers.get("retry-after") as string }
          : {}),
      },
    });
  }

  const tokens = (await loginResponse.json()) as TokenPayload;

  let meResponse: Response;
  try {
    meResponse = await fetch(backendUrl("/users/me"), {
      headers: {
        authorization: `Bearer ${tokens.access_token}`,
        "x-tenant-id": tenantSlug,
        accept: "application/json",
      },
      cache: "no-store",
    });
  } catch {
    return problem(503, "api_unavailable", "Layanan sedang tidak tersedia");
  }

  if (!meResponse.ok) {
    return problem(502, "profile_unavailable", "Tidak dapat memuat profil akun");
  }

  const me = (await meResponse.json()) as MePayload;
  if (!me.membership) {
    return problem(403, "tenant_required", "Akun ini tidak terhubung ke faskes");
  }

  const sid = await createSession({
    user_id: me.id,
    tenant_id: me.membership.tenant.id,
    tenant_slug: me.membership.tenant.slug,
    role: me.membership.role,
    is_platform_admin: me.is_platform_admin,
    access_token: tokens.access_token,
    refresh_token: tokens.refresh_token,
    csrf: crypto.randomUUID(),
    created_at: new Date().toISOString(),
  });

  if (!sid) {
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

  const session = await readSession();
  if (session) {
    let allSessions = false;
    try {
      const body = (await request.json()) as { all_sessions?: boolean };
      allSessions = Boolean(body.all_sessions);
    } catch {
      allSessions = false;
    }
    try {
      await fetch(backendUrl("/auth/logout"), {
        method: "POST",
        headers: {
          authorization: `Bearer ${session.data.access_token}`,
          "x-tenant-id": session.data.tenant_slug,
          "content-type": "application/json",
        },
        body: JSON.stringify({ all_sessions: allSessions }),
        cache: "no-store",
      });
    } catch {
      // Local session removal still matters when the API is unreachable.
    }
    await destroySession(session.sid);
  } else {
    await destroySession();
  }

  return new NextResponse(null, { status: 204 });
}