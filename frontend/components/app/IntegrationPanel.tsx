"use client";

import { useEffect, useState } from "react";

import { StatusBadge } from "@/components/app/StatusBadge";
import { formatDateTime } from "@/lib/format";
import type {
  IntegrationCredentials,
  JobList,
  SyncJob,
} from "@/lib/types";

type Problem = { code?: string; detail?: string; title?: string };

const ACTIVE = new Set(["queued", "running"]);

export function IntegrationPanel({
  initialCredentials,
  initialJobs,
}: {
  initialCredentials: IntegrationCredentials | null;
  initialJobs: SyncJob[];
}) {
  const [credentials, setCredentials] = useState(initialCredentials);
  const [jobs, setJobs] = useState(initialJobs);
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasActive = jobs.some((job) => ACTIVE.has(job.status));

  useEffect(() => {
    if (!hasActive) return;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(
          "/api/app/integrations/satusehat/jobs?limit=20",
        );
        if (response.ok) {
          const data = (await response.json()) as JobList;
          setJobs(data.items);
        }
      } catch {
        // Transient polling failure; the next tick retries.
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [hasActive]);

  async function refreshCredentials() {
    const response = await fetch("/api/app/integrations/satusehat");
    if (response.ok) {
      setCredentials((await response.json()) as IntegrationCredentials);
    }
  }

  async function refreshJobs() {
    const response = await fetch("/api/app/integrations/satusehat/jobs?limit=20");
    if (response.ok) {
      setJobs(((await response.json()) as JobList).items);
    }
  }

  async function saveCredentials(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending("save");
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/app/integrations/satusehat", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_id: String(data.get("client_id") ?? ""),
          client_secret: String(data.get("client_secret") ?? ""),
          organization_id: String(data.get("organization_id") ?? ""),
        }),
      });
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as Problem;
        setError(
          problem.code === "invalid_credentials_shape"
            ? "Client ID dan Organization ID wajib diisi."
            : problem.detail || problem.title || "Kredensial gagal disimpan.",
        );
        return;
      }
      setCredentials((await response.json()) as IntegrationCredentials);
      form.reset();
      setMessage("Kredensial disimpan. Jalankan uji koneksi sebelum sinkronisasi.");
    } catch {
      setError("Koneksi terputus. Coba lagi.");
    } finally {
      setPending(null);
    }
  }

  async function testConnection() {
    setPending("test");
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/app/integrations/satusehat/test", {
        method: "POST",
      });
      const payload = (await response.json().catch(() => ({}))) as {
        status?: string;
        latency_ms?: number;
        error?: string;
        detail?: string;
      };
      if (!response.ok) {
        setError(payload.detail || "Uji koneksi gagal dijalankan.");
        return;
      }
      if (payload.status === "connected") {
        setMessage(`Koneksi berhasil (${payload.latency_ms ?? 0} ms).`);
      } else {
        setError(payload.error || "Koneksi gagal. Periksa kredensial.");
      }
      await refreshCredentials();
    } catch {
      setError("Koneksi terputus. Coba lagi.");
    } finally {
      setPending(null);
    }
  }

  async function enqueue(kind: "organization" | "patient") {
    setPending(`sync-${kind}`);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/app/integrations/satusehat/sync", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind }),
      });
      const payload = (await response.json().catch(() => ({}))) as {
        job_id?: string;
        status?: string;
        code?: string;
        detail?: string;
      };
      if (!response.ok) {
        setError(
          payload.code === "credentials_not_verified"
            ? "Uji koneksi terlebih dahulu sebelum menjalankan sinkronisasi."
            : payload.detail || "Sinkronisasi gagal diantrekan.",
        );
        return;
      }
      setMessage(`Job ${kind} diantrekan (${payload.status ?? "queued"}).`);
      await refreshJobs();
    } catch {
      setError("Koneksi terputus. Coba lagi.");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-[10px] border border-[#f0dfbc] bg-[#fff6e5] px-4 py-3 text-sm text-[var(--warn)]">
        Mode uji: kredensial diarahkan ke mock SATUSEHAT. Tidak ada trafik
        produksi Kemenkes.
      </div>

      {message ? (
        <p role="status" className="rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] px-4 py-3 text-sm text-[var(--brand-ink)]">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-4 py-3 text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Kredensial SATUSEHAT</h2>
              <p className="mt-1 text-xs text-[var(--muted)]">
                Secret disimpan terenkripsi dan tidak dapat ditampilkan kembali.
              </p>
            </div>
            <StatusBadge status={credentials?.status ?? "unverified"} />
          </div>

          <form onSubmit={saveCredentials} className="mt-4 space-y-4">
            <div>
              <label htmlFor="client_id" className="text-sm font-medium">
                Client ID
              </label>
              <input
                id="client_id"
                name="client_id"
                required
                defaultValue={credentials?.client_id ?? ""}
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div>
              <label htmlFor="organization_id" className="text-sm font-medium">
                Organization ID
              </label>
              <input
                id="organization_id"
                name="organization_id"
                required
                defaultValue={credentials?.organization_id ?? ""}
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div>
              <label htmlFor="client_secret" className="text-sm font-medium">
                Client secret
              </label>
              <input
                id="client_secret"
                name="client_secret"
                type="password"
                autoComplete="new-password"
                placeholder={
                  credentials?.has_secret
                    ? "Biarkan kosong untuk mempertahankan secret"
                    : "Masukkan client secret"
                }
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
              {credentials?.has_secret ? (
                <p className="mt-1 text-xs text-[var(--muted)]">
                  Secret sudah tersimpan. Mengisi kolom ini akan menggantinya.
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="submit"
                disabled={pending !== null}
                className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {pending === "save" ? "Menyimpan…" : "Simpan kredensial"}
              </button>
              <button
                type="button"
                onClick={() => void testConnection()}
                disabled={pending !== null || !credentials}
                className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-5 text-sm font-semibold disabled:opacity-60"
              >
                {pending === "test" ? "Menguji…" : "Uji koneksi"}
              </button>
            </div>
          </form>

          <dl className="mt-5 space-y-2 border-t border-[var(--line)] pt-4 text-xs text-[var(--ink-2)]">
            <div className="flex justify-between gap-3">
              <dt>Base URL</dt>
              <dd className="truncate text-right">{credentials?.base_url ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt>Terakhir diuji</dt>
              <dd>{formatDateTime(credentials?.last_verified_at)}</dd>
            </div>
            {credentials?.last_error ? (
              <div>
                <dt className="text-[var(--danger)]">Error terakhir</dt>
                <dd className="mt-1 break-words text-[var(--danger)]">
                  {credentials.last_error}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>

        <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
          <h2 className="text-sm font-semibold">Sinkronisasi</h2>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Antrean diproses worker. Sinkronisasi ulang memakai pemetaan yang
            sama dan tidak membuat duplikat.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void enqueue("organization")}
              disabled={pending !== null || credentials?.status !== "connected"}
              className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white disabled:opacity-60"
            >
              {pending === "sync-organization" ? "Mengantrekan…" : "Sinkronkan organisasi"}
            </button>
            <button
              type="button"
              onClick={() => void enqueue("patient")}
              disabled={pending !== null || credentials?.status !== "connected"}
              className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-5 text-sm font-semibold disabled:opacity-60"
            >
              {pending === "sync-patient" ? "Mengantrekan…" : "Sinkronkan pasien demo"}
            </button>
          </div>
          {credentials?.status !== "connected" ? (
            <p className="mt-2 text-xs text-[var(--warn)]">
              Sinkronisasi aktif setelah uji koneksi berhasil.
            </p>
          ) : null}

          <h3 className="mt-6 text-sm font-semibold">Riwayat job</h3>
          {jobs.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--ink-2)]">
              Belum ada job. Jalankan sinkronisasi setelah koneksi teruji.
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
              {jobs.map((job) => (
                <li key={job.id} className="rounded-md border border-[var(--line)] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{job.kind}</p>
                    <StatusBadge status={job.status} />
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {formatDateTime(job.created_at)} · {job.attempts} percobaan
                  </p>
                  {job.fhir_id ? (
                    <p className="mt-1 break-all text-xs text-[var(--ink-2)]">
                      FHIR ID: <span className="font-mono">{job.fhir_id}</span>
                    </p>
                  ) : null}
                  {job.last_error ? (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer font-medium text-[var(--danger)]">
                        Detail kesalahan
                      </summary>
                      <p className="mt-1 break-words text-[var(--danger)]">
                        {job.last_error}
                      </p>
                    </details>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
          {hasActive ? (
            <p className="mt-3 text-xs text-[var(--muted)]">
              Memperbarui otomatis setiap 4 detik…
            </p>
          ) : null}
        </section>
      </div>
    </div>
  );
}