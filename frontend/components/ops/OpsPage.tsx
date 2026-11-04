import { redirect } from "next/navigation";

import { OpsShell } from "@/components/ops/OpsShell";
import { ApiError } from "@/lib/api";
import { opsApiRequest, OpsSessionExpiredError } from "@/lib/ops-api";
import { readOpsSession } from "@/lib/ops-session";
import type { MeResponse } from "@/lib/types";

export async function OpsPage({
  next,
  children,
}: {
  next: string;
  children: React.ReactNode;
}) {
  const session = await readOpsSession();
  if (!session) redirect(`/ops/masuk?next=${encodeURIComponent(next)}`);

  let me: MeResponse;
  try {
    me = await opsApiRequest<MeResponse>(session, "/users/me");
  } catch (error) {
    if (error instanceof OpsSessionExpiredError) {
      redirect(`/ops/masuk?next=${encodeURIComponent(next)}`);
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <div className="grid min-h-dvh place-items-center bg-[var(--bg-alt)] px-4">
          <div className="max-w-md rounded-[10px] border border-[var(--line)] bg-white p-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
              403
            </p>
            <h1 className="h2 mt-3">Akses operator diperlukan</h1>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              Akun ini bukan operator platform. Tidak ada menu operator yang
              ditampilkan untuk akun biasa.
            </p>
            <a
              href="/masuk"
              className="mt-6 inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white"
            >
              Ke aplikasi faskes
            </a>
          </div>
        </div>
      );
    }
    if (error instanceof ApiError) {
      return (
        <div className="grid min-h-dvh place-items-center bg-[var(--bg-alt)] px-4">
          <div className="max-w-md rounded-[10px] border border-[var(--line)] bg-white p-8 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
              Operator
            </p>
            <h1 className="h2 mt-3">Layanan sedang tidak tersedia</h1>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              Profil operator tidak dapat dimuat. Coba lagi beberapa saat lagi.
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

  if (!me.is_platform_admin) redirect("/ops/masuk");

  return <OpsShell email={me.email}>{children}</OpsShell>;
}