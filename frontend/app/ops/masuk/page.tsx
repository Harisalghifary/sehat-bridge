import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { OpsLoginForm } from "@/components/ops/OpsLoginForm";
import { readOpsSession } from "@/lib/ops-session";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Masuk operator",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function OpsLoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const session = await readOpsSession();
  if (session) redirect("/ops/tenant");

  const params = await searchParams;
  const next =
    params.next && params.next.startsWith("/ops") ? params.next : "/ops/tenant";

  return (
    <div className="grid min-h-dvh place-items-center bg-[var(--ink)] px-4 py-10">
      <div className="w-full max-w-[420px]">
        <div className="mb-5 flex items-center gap-2.5 text-white">
          <span
            aria-hidden="true"
            className="grid size-9 place-items-center rounded-lg bg-white text-xs font-bold text-[var(--ink)]"
          >
            SB
          </span>
          <div>
            <p className="text-sm font-semibold">Sehat Bridge</p>
            <p className="text-[11px] uppercase tracking-[0.16em] text-white/60">
              Konsol operator
            </p>
          </div>
        </div>
        <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
          <h1 className="text-2xl font-semibold tracking-tight">Masuk operator</h1>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
            Akun platform tanpa tenant. Konsol ini lintas-tenant dan hanya untuk
            operator yang berwenang.
          </p>
          <div className="mt-6">
            <OpsLoginForm next={next} />
          </div>
        </div>
        <p className="mt-4 text-center text-xs text-white/55">{site.disclaimer}</p>
      </div>
    </div>
  );
}