import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AppPage } from "@/components/app/AppPage";
import { PageHeader } from "@/components/app/PageHeader";
import {
  ApiError,
  apiRequest,
  fetchReadiness,
  SessionExpiredError,
} from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import { readSession } from "@/lib/session";
import type {
  FileList,
  FileUsage,
  IntegrationCredentials,
  JobList,
} from "@/lib/types";

export const metadata: Metadata = { title: "Dasbor" };

export default async function DashboardPage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/dasbor");
  const isAdmin = session.data.role === "owner" || session.data.role === "admin";

  try {
    const [usage, files, jobs, credentials, readiness] = await Promise.all([
      apiRequest<FileUsage>(session, "/files/usage"),
      apiRequest<FileList>(session, "/files?limit=5"),
      isAdmin
        ? apiRequest<JobList>(session, "/integrations/satusehat/jobs?limit=5")
        : Promise.resolve({ items: [], next_cursor: null, has_more: false }),
      isAdmin
        ? apiRequest<IntegrationCredentials>(
            session,
            "/integrations/satusehat",
          ).catch((error: unknown) => {
            if (error instanceof ApiError && error.status === 404) return null;
            throw error;
          })
        : Promise.resolve(null),
      fetchReadiness(),
    ]);

    const latestJob = jobs.items[0] ?? null;
    const percent =
      usage.quota_bytes > 0
        ? Math.min(100, Math.round((usage.used_bytes / usage.quota_bytes) * 100))
        : 0;

    const attention: { label: string; href: string; body: string }[] = [];
    if (isAdmin && latestJob && ["failed", "dead"].includes(latestJob.status)) {
      attention.push({
        label: "Sinkronisasi gagal",
        href: "/app/integrasi",
        body: "Ada job yang berhenti. Periksa detail kesalahan di halaman integrasi.",
      });
    }
    if (isAdmin && credentials && credentials.status !== "connected") {
      attention.push({
        label: "Integrasi belum terverifikasi",
        href: "/app/integrasi",
        body: "Uji koneksi sebelum menjalankan sinkronisasi berikutnya.",
      });
    }
    if (percent >= 90) {
      attention.push({
        label: "Kuota hampir penuh",
        href: "/app/berkas",
        body: `${percent}% kuota terpakai. Hapus berkas lama atau minta penambahan kuota.`,
      });
    }

    const activity = [
      ...files.items.map((file) => ({
        at: file.created_at,
        title: `Berkas ${file.filename}`,
        detail: `${file.status === "ready" ? "Siap" : "Mengunggah"} · ${formatBytes(file.size_bytes)}`,
      })),
      ...jobs.items.map((job) => ({
        at: job.created_at,
        title: `Sinkronisasi ${job.kind}`,
        detail: `Status ${job.status} · ${job.attempts} percobaan`,
      })),
    ]
      .sort((a, b) => (a.at < b.at ? 1 : -1))
      .slice(0, 6);

    return (
      <AppPage next="/app/dasbor">
      <div className="space-y-6">
        <PageHeader
          title="Dasbor faskes"
          description="Ringkasan berkas, kuota, dan integrasi faskes Anda. Semua angka berasal dari API."
        />

        <section
          aria-label="Kesiapan layanan"
          className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-[10px] border border-[var(--line)] bg-white px-4 py-3 text-sm"
        >
          <span
            aria-hidden="true"
            className={`size-2.5 rounded-full ${
              readiness?.status === "ok"
                ? "bg-[var(--ok)]"
                : readiness
                  ? "bg-[var(--danger)]"
                  : "bg-[var(--line)]"
            }`}
          />
          <span className="font-medium">
            {readiness
              ? readiness.status === "ok"
                ? "Layanan siap"
                : "Layanan terganggu"
              : "Status layanan tidak diketahui"}
          </span>
          <span className="text-xs text-[var(--muted)]">
            {readiness
              ? Object.entries(readiness.checks)
                  .map(([name, state]) => `${name} ${state}`)
                  .join(" · ")
              : "Tidak dapat membaca readiness API"}
          </span>
        </section>

        <section aria-label="Ringkasan" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Stat label="Berkas tersimpan" value={String(usage.files)} detail="Tidak termasuk yang dihapus" />
          <Stat
            label="Kuota terpakai"
            value={`${percent}%`}
            detail={`${formatBytes(usage.used_bytes)} dari ${formatBytes(usage.quota_bytes)}`}
          />
          <Stat
            label="Sinkronisasi terakhir"
            value={latestJob ? statusLabel(latestJob.status) : "Belum ada"}
            detail={latestJob ? formatDateTime(latestJob.created_at) : "Belum pernah dijalankan"}
          />
          <Stat
            label="Status integrasi"
            value={
              !isAdmin
                ? "Khusus admin"
                : credentials
                  ? statusLabel(credentials.status)
                  : "Belum diatur"
            }
            detail={
              !isAdmin
                ? "Hubungi admin faskes"
                : credentials
                  ? `Mode ${credentials.mode}`
                  : "Belum ada kredensial"
            }
          />
        </section>

        <section
          aria-labelledby="quota-title"
          className="rounded-[10px] border border-[var(--line)] bg-white p-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="quota-title" className="text-sm font-semibold">
              Kuota penyimpanan
            </h2>
            <p className="text-sm text-[var(--ink-2)]">
              {formatBytes(usage.used_bytes)} / {formatBytes(usage.quota_bytes)}
            </p>
          </div>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent}
            aria-label="Persentase kuota terpakai"
            className="mt-3 h-2 overflow-hidden rounded-full bg-[var(--line)]"
          >
            <div
              className="h-2 rounded-full bg-[var(--brand)]"
              style={{ width: `${percent}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-[var(--muted)]">
            {percent}% terpakai · batas unggahan 25 MB per berkas
          </p>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <section
            aria-labelledby="activity-title"
            className="rounded-[10px] border border-[var(--line)] bg-white p-5"
          >
            <div className="flex items-center justify-between gap-2">
              <h2 id="activity-title" className="text-sm font-semibold">
                Aktivitas terbaru
              </h2>
              <Link
                href="/app/berkas"
                className="text-xs font-semibold text-[var(--brand)] underline underline-offset-4"
              >
                Lihat berkas
              </Link>
            </div>
            {activity.length ? (
              <ul className="mt-3 divide-y divide-[var(--line)]">
                {activity.map((item) => (
                  <li key={`${item.at}-${item.title}`} className="py-3">
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="mt-0.5 text-xs text-[var(--muted)]">
                      {item.detail} · {formatDateTime(item.at)}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-[var(--ink-2)]">
                Belum ada aktivitas. Mulai dengan mengunggah berkas pertama.
              </p>
            )}
          </section>

          <section
            aria-labelledby="attention-title"
            className="rounded-[10px] border border-[var(--line)] bg-white p-5"
          >
            <h2 id="attention-title" className="text-sm font-semibold">
              Yang perlu perhatian
            </h2>
            {attention.length ? (
              <ul className="mt-3 space-y-3">
                {attention.map((item) => (
                  <li key={item.label} className="rounded-md bg-[var(--bg-alt)] p-3">
                    <Link
                      href={item.href}
                      className="text-sm font-semibold text-[var(--brand)] underline underline-offset-4"
                    >
                      {item.label}
                    </Link>
                    <p className="mt-1 text-xs leading-5 text-[var(--ink-2)]">
                      {item.body}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-3 space-y-3 text-sm text-[var(--ink-2)]">
                <p>Tidak ada peringatan dari data saat ini.</p>
                {usage.files === 0 ? (
                  <Link
                    href="/app/berkas"
                    className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-4 text-sm font-semibold text-white"
                  >
                    Unggah berkas pertama
                  </Link>
                ) : null}
              </div>
            )}
          </section>
        </div>

        <p className="text-xs text-[var(--muted)]">
          Data dimuat langsung dari API pada {formatDateTime(new Date().toISOString())}.
        </p>
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/dasbor");
    }
    throw error;
  }
}

function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "Antre",
    running: "Berjalan",
    done: "Selesai",
    failed: "Gagal",
    dead: "Berhenti",
    unverified: "Belum diuji",
    connected: "Terhubung",
    error: "Error",
  };
  return labels[status] ?? status;
}