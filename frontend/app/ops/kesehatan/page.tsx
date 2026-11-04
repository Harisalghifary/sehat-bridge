import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { OpsPage } from "@/components/ops/OpsPage";
import { ApiError } from "@/lib/api";
import { opsApiRequest, OpsSessionExpiredError } from "@/lib/ops-api";
import { readOpsSession } from "@/lib/ops-session";
import type { OpsHealth } from "@/lib/ops-types";

export const metadata: Metadata = {
  title: "Kesehatan · Operator",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

function uptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts = [];
  if (days) parts.push(`${days} hari`);
  if (hours) parts.push(`${hours} jam`);
  parts.push(`${minutes} menit`);
  return parts.join(" ");
}

const CHECK_LABEL: Record<string, string> = {
  postgres: "PostgreSQL",
  redis: "Redis",
  minio: "MinIO",
};

export default async function OpsHealthPage() {
  const session = await readOpsSession();
  if (!session) redirect("/ops/masuk?next=/ops/kesehatan");

  try {
    const health = await opsApiRequest<OpsHealth>(session, "/admin/health");

    return (
      <OpsPage next="/ops/kesehatan">
        <div className="space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Kesehatan</h1>
              <p className="mt-1 text-sm text-[var(--ink-2)]">
                Status dependensi, versi, uptime proses API, dan kedalaman antrean
                sinkronisasi lintas-tenant.
              </p>
            </div>
            <Link
              href="/ops/kesehatan"
              className="inline-flex min-h-11 items-center justify-center rounded-md border border-[var(--line)] bg-white px-4 text-sm font-semibold"
            >
              Muat ulang
            </Link>
          </div>

          <div
            role="status"
            className={`rounded-[10px] border px-4 py-3 text-sm font-medium ${
              health.status === "ok"
                ? "border-[#cbe6e2] bg-[var(--brand-weak)] text-[var(--brand-ink)]"
                : "border-[#f0c9cb] bg-[#fdf0f0] text-[var(--danger)]"
            }`}
          >
            {health.status === "ok"
              ? "Semua dependensi merespons normal."
              : "Satu atau lebih dependensi bermasalah."}
          </div>

          <section aria-labelledby="deps-title">
            <h2 id="deps-title" className="text-sm font-semibold">
              Dependensi
            </h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              {Object.entries(health.checks).map(([name, state]) => (
                <div
                  key={name}
                  className="rounded-[10px] border border-[var(--line)] bg-white p-4"
                >
                  <p className="text-xs uppercase tracking-wide text-[var(--muted)]">
                    {CHECK_LABEL[name] ?? name}
                  </p>
                  <p className="mt-1 flex items-center gap-2 text-sm font-semibold">
                    <span
                      aria-hidden="true"
                      className={`size-2.5 rounded-full ${
                        state === "ok" ? "bg-[var(--ok)]" : "bg-[var(--danger)]"
                      }`}
                    />
                    {state === "ok" ? "Normal" : "Error"}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section
              aria-labelledby="runtime-title"
              className="rounded-[10px] border border-[var(--line)] bg-white p-5"
            >
              <h2 id="runtime-title" className="text-sm font-semibold">
                Runtime
              </h2>
              <dl className="mt-4 space-y-3 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--ink-2)]">Versi</dt>
                  <dd className="font-mono font-medium">{health.version}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--ink-2)]">Uptime</dt>
                  <dd className="font-medium">{uptime(health.uptime_seconds)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-[var(--ink-2)]">Status</dt>
                  <dd className="font-medium">{health.status}</dd>
                </div>
              </dl>
            </section>

            <section
              aria-labelledby="queue-title"
              className="rounded-[10px] border border-[var(--line)] bg-white p-5"
            >
              <h2 id="queue-title" className="text-sm font-semibold">
                Antrean sinkronisasi
              </h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                {Object.entries(health.queue).map(([name, count]) => (
                  <div key={name} className="rounded-md bg-[var(--bg-alt)] p-3">
                    <dt className="text-xs capitalize text-[var(--muted)]">{name}</dt>
                    <dd className="mt-1 text-xl font-semibold">{count}</dd>
                  </div>
                ))}
              </dl>
            </section>
          </div>

          <section
            aria-labelledby="tenants-title"
            className="rounded-[10px] border border-[var(--line)] bg-white p-5"
          >
            <h2 id="tenants-title" className="text-sm font-semibold">
              Tenant menurut status
            </h2>
            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              {Object.entries(health.tenants).map(([name, count]) => (
                <div key={name} className="rounded-md bg-[var(--bg-alt)] p-3">
                  <dt className="text-xs capitalize text-[var(--muted)]">{name}</dt>
                  <dd className="mt-1 text-xl font-semibold">{count}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </OpsPage>
    );
  } catch (error) {
    if (error instanceof OpsSessionExpiredError) {
      redirect("/ops/masuk?next=/ops/kesehatan");
    }
    if (error instanceof ApiError && error.status === 403) {
      redirect("/ops/masuk");
    }
    throw error;
  }
}