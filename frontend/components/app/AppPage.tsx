import { redirect } from "next/navigation";

import { AppShell } from "@/components/app/AppShell";
import { TenantSuspended } from "@/components/app/TenantSuspended";
import { ApiError, apiRequest, SessionExpiredError } from "@/lib/api";
import { appNav } from "@/lib/app-nav";
import { readSession } from "@/lib/session";
import type { MeResponse } from "@/lib/types";

/**
 * Explicit app-shell wrapper.
 *
 * The shell deliberately lives in a component rather than an `/app` layout:
 * Next 15 on Linux hoisted `app/app/layout.tsx` over sibling route groups in
 * this project, wrapping the marketing site with the private shell. Wrapping
 * each private page keeps the URL structure and scopes the shell correctly.
 */
export async function AppPage({
  next,
  children,
}: {
  next: string;
  children: React.ReactNode;
}) {
  const session = await readSession();
  if (!session) redirect(`/masuk?next=${encodeURIComponent(next)}`);

  let me: MeResponse;
  try {
    me = await apiRequest<MeResponse>(session, "/users/me");
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect(`/masuk?next=${encodeURIComponent(next)}`);
    }
    if (error instanceof ApiError && error.code === "tenant_inactive") {
      return <TenantSuspended tenant={session.data.tenant_slug} />;
    }
    if (error instanceof ApiError) {
      return (
        <div className="grid min-h-dvh place-items-center bg-[var(--bg-alt)] px-4">
          <div className="max-w-md rounded-[10px] border border-[var(--line)] bg-white p-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
              Aplikasi
            </p>
            <h1 className="h2 mt-3">Layanan sedang tidak tersedia</h1>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              Kami tidak dapat memuat profil akun. Sesi Anda tetap tersimpan;
              coba muat ulang halaman beberapa saat lagi.
            </p>
            <a
              href={next}
              className="mt-6 inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white"
            >
              Coba lagi
            </a>
          </div>
        </div>
      );
    }
    throw error;
  }

  if (!me.membership) redirect("/masuk");

  const role = me.membership.role;
  const nav = appNav
    .filter((item) => item.roles.includes(role))
    .map(({ href, label, icon }) => ({ href, label, icon }));

  return (
    <AppShell
      nav={nav}
      isPlatformAdmin={me.is_platform_admin}
      user={{
        name: me.profile?.display_name || me.email,
        email: me.email,
        role,
        tenantName: me.membership.tenant.name,
        tenantSlug: me.membership.tenant.slug,
      }}
    >
      {children}
    </AppShell>
  );
}