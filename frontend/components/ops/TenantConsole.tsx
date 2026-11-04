"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { formatDate, formatDateTime } from "@/lib/format";
import type {
  OpsTenant,
  OpsTenantDetail,
  ProvisionResponse,
} from "@/lib/ops-types";

type Problem = { code?: string; detail?: string; title?: string };

const STATUS_LABEL: Record<string, string> = {
  active: "Aktif",
  suspended: "Ditangguhkan",
  provisioning: "Provisi",
  failed: "Gagal",
};

const STATUS_TONE: Record<string, string> = {
  active: "bg-[var(--brand-weak)] text-[var(--brand-ink)] border-[#cbe6e2]",
  suspended: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
  provisioning: "bg-[var(--bg-alt)] text-[var(--ink-2)] border-[var(--line)]",
  failed: "bg-[#fdf0f0] text-[var(--danger)] border-[#f0c9cb]",
};

function OpsStatus({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${
        STATUS_TONE[status] ?? STATUS_TONE.provisioning
      }`}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

export function TenantConsole({ initial }: { initial: OpsTenant[] }) {
  const router = useRouter();
  const [tenants, setTenants] = useState(initial);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<OpsTenantDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmSuspend, setConfirmSuspend] = useState(false);
  const [provisionResult, setProvisionResult] = useState<ProvisionResponse | null>(
    null,
  );
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (pending !== "provision") return;
    const started = Date.now();
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - started) / 1000));
    }, 250);
    return () => clearInterval(timer);
  }, [pending]);

  async function loadDetail(slug: string) {
    setSelected(slug);
    setDetail(null);
    setDetailError(null);
    setConfirmSuspend(false);
    setDetailLoading(true);
    try {
      const response = await fetch(`/api/ops/tenants/${slug}`);
      if (response.status === 401) {
        router.replace("/ops/masuk?next=/ops/tenant");
        return;
      }
      if (!response.ok) {
        setDetailError("Detail tenant gagal dimuat.");
        return;
      }
      setDetail((await response.json()) as OpsTenantDetail);
    } catch {
      setDetailError("Koneksi terputus saat memuat detail.");
    } finally {
      setDetailLoading(false);
    }
  }

  function setDetailError(value: string | null) {
    setError(value);
  }

  async function refreshTenants() {
    const response = await fetch("/api/ops/tenants");
    if (response.ok) {
      const data = (await response.json()) as { items: OpsTenant[] };
      setTenants(data.items);
    }
  }

  async function provision(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending("provision");
    setError(null);
    setMessage(null);
    setProvisionResult(null);
    setElapsed(0);
    const started = performance.now();
    try {
      const response = await fetch("/api/ops/tenants", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          slug: String(data.get("slug") ?? "").trim().toLowerCase(),
          name: String(data.get("name") ?? "").trim(),
          owner_email: String(data.get("owner_email") ?? "").trim(),
          owner_display_name:
            String(data.get("owner_display_name") ?? "").trim() || null,
          password: String(data.get("password") ?? ""),
        }),
      });
      if (response.status === 401) {
        router.replace("/ops/masuk?next=/ops/tenant");
        return;
      }
      const payload = (await response.json().catch(() => ({}))) as
        | ProvisionResponse
        | Problem;
      if (!response.ok) {
        const problem = payload as Problem;
        setError(
          problem.code === "tenant_exists"
            ? "Slug tenant sudah dipakai. Pilih slug lain."
            : problem.code === "validation_error"
              ? "Periksa kembali isian. Sandi minimal 12 karakter."
              : problem.detail || problem.title || "Tenant gagal dibuat.",
        );
        return;
      }
      const result = payload as ProvisionResponse;
      const seconds = (performance.now() - started) / 1000;
      setProvisionResult({
        ...result,
        tenant: { ...result.tenant, created_at: result.tenant.created_at },
      });
      setMessage(
        `Tenant ${result.tenant.slug} aktif dalam ${seconds.toFixed(1)} detik.`,
      );
      form.reset();
      await refreshTenants();
      await loadDetail(result.tenant.slug);
    } catch {
      setError("Koneksi terputus saat membuat tenant.");
    } finally {
      setPending(null);
    }
  }

  async function changeStatus(slug: string, action: "suspend" | "resume") {
    setPending(action);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch(`/api/ops/tenants/${slug}/${action}`, {
        method: "POST",
      });
      if (response.status === 401) {
        router.replace("/ops/masuk?next=/ops/tenant");
        return;
      }
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as Problem;
        setError(problem.detail || problem.title || "Status tenant gagal diubah.");
        return;
      }
      const data = (await response.json()) as { tenant: OpsTenant };
      setDetail((current) =>
        current ? { ...current, ...data.tenant } : current,
      );
      setTenants((items) =>
        items.map((item) => (item.slug === slug ? { ...item, ...data.tenant } : item)),
      );
      setConfirmSuspend(false);
      setMessage(
        action === "suspend"
          ? `Tenant ${slug} ditangguhkan. Login dan API tenant diblokir.`
          : `Tenant ${slug} diaktifkan kembali.`,
      );
    } catch {
      setError("Koneksi terputus saat mengubah status.");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Tenant</h1>
          <p className="mt-1 text-sm text-[var(--ink-2)]">
            Daftar faskes, detail, provisi, dan penangguhan. Semua tindakan
            dicatat pada audit.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setFormOpen((value) => !value);
            setProvisionResult(null);
          }}
          aria-expanded={formOpen}
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white hover:bg-[var(--brand-ink)]"
        >
          {formOpen ? "Tutup formulir" : "Provisi tenant baru"}
        </button>
      </div>

      {message ? (
        <p
          role="status"
          className="rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] px-4 py-3 text-sm text-[var(--brand-ink)]"
        >
          {message}
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-4 py-3 text-sm text-[var(--danger)]"
        >
          {error}
        </p>
      ) : null}

      {formOpen ? (
        <section
          aria-labelledby="provision-title"
          className="rounded-[10px] border border-[var(--line)] bg-white p-5"
        >
          <h2 id="provision-title" className="text-sm font-semibold">
            Provisi tenant
          </h2>
          <p className="mt-1 text-xs text-[var(--ink-2)]">
            Slug dipakai pada URL internal dan tidak dapat diubah lewat UI.
          </p>
          <form onSubmit={provision} className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="tenant-slug" className="text-sm font-medium">
                Slug
              </label>
              <input
                id="tenant-slug"
                name="slug"
                required
                minLength={2}
                maxLength={63}
                pattern="[a-z0-9][a-z0-9_-]{1,62}"
                placeholder="klinik-sehat"
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div>
              <label htmlFor="tenant-name" className="text-sm font-medium">
                Nama faskes
              </label>
              <input
                id="tenant-name"
                name="name"
                required
                minLength={2}
                maxLength={120}
                placeholder="Klinik Sehat"
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div>
              <label htmlFor="owner-email" className="text-sm font-medium">
                Email owner
              </label>
              <input
                id="owner-email"
                name="owner_email"
                type="email"
                required
                placeholder="owner@klinik.example"
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div>
              <label htmlFor="owner-name" className="text-sm font-medium">
                Nama owner (opsional)
              </label>
              <input
                id="owner-name"
                name="owner_display_name"
                maxLength={120}
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="owner-password" className="text-sm font-medium">
                Sandi awal owner
              </label>
              <input
                id="owner-password"
                name="password"
                type="password"
                required
                minLength={12}
                autoComplete="new-password"
                className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
              />
              <p className="mt-1 text-xs text-[var(--muted)]">
                Minimal 12 karakter. Sampaikan lewat kanal aman; pengguna dapat
                menggantinya nanti.
              </p>
            </div>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={pending !== null}
                className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {pending === "provision"
                  ? `Memproses… ${elapsed}s`
                  : "Buat tenant"}
              </button>
            </div>
          </form>

          {pending === "provision" ? (
            <div className="mt-4 rounded-md border border-[var(--line)] bg-[var(--bg-alt)] p-4">
              <p className="text-sm font-medium">Provisi berjalan…</p>
              <ol className="mt-2 space-y-1 text-sm text-[var(--ink-2)]">
                <li>1. Membuat skema tenant</li>
                <li>2. Menjalankan migrasi tenant</li>
                <li>3. Menyiapkan akun owner</li>
              </ol>
              <p className="mt-2 text-xs text-[var(--muted)]">{elapsed} detik</p>
            </div>
          ) : null}

          {provisionResult ? (
            <div className="mt-4 rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] p-4">
              <p className="text-sm font-semibold text-[var(--brand-ink)]">
                Provisi selesai
              </p>
              <ol className="mt-2 space-y-1 text-sm text-[var(--brand-ink)]">
                {provisionResult.steps.map((step) => (
                  <li key={step.key}>
                    {step.status === "done" ? "✓" : "×"} {step.label}
                  </li>
                ))}
              </ol>
              <p className="mt-2 text-xs text-[var(--brand-ink)]">
                Owner: {provisionResult.owner_email}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      <div className="hidden overflow-hidden rounded-[10px] border border-[var(--line)] bg-white md:block">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--bg-alt)] text-xs uppercase tracking-wide text-[var(--muted)]">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">Faskes</th>
              <th scope="col" className="px-4 py-3 font-medium">Status</th>
              <th scope="col" className="px-4 py-3 font-medium">Anggota</th>
              <th scope="col" className="px-4 py-3 font-medium">Owner</th>
              <th scope="col" className="px-4 py-3 font-medium">Dibuat</th>
              <th scope="col" className="px-4 py-3 text-right font-medium">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {tenants.map((tenant) => (
              <tr key={tenant.slug}>
                <td className="px-4 py-3">
                  <p className="font-medium">{tenant.name}</p>
                  <p className="text-xs text-[var(--muted)]">{tenant.slug}</p>
                </td>
                <td className="px-4 py-3"><OpsStatus status={tenant.status} /></td>
                <td className="px-4 py-3">{tenant.members}</td>
                <td className="max-w-[220px] truncate px-4 py-3 text-[var(--ink-2)]">
                  {tenant.owner_email ?? "—"}
                </td>
                <td className="px-4 py-3 text-[var(--ink-2)]">
                  {formatDate(tenant.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => void loadDetail(tenant.slug)}
                    className="min-h-9 rounded border border-[var(--line)] px-2.5 text-xs font-medium hover:bg-[var(--bg-alt)]"
                  >
                    Lihat
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 md:hidden">
        {tenants.map((tenant) => (
          <li
            key={tenant.slug}
            className="rounded-[10px] border border-[var(--line)] bg-white p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold">{tenant.name}</p>
                <p className="text-xs text-[var(--muted)]">{tenant.slug}</p>
              </div>
              <OpsStatus status={tenant.status} />
            </div>
            <p className="mt-2 text-xs text-[var(--ink-2)]">
              {tenant.members} anggota · dibuat {formatDate(tenant.created_at)}
            </p>
            <p className="mt-1 truncate text-xs text-[var(--muted)]">
              {tenant.owner_email ?? "Tanpa owner"}
            </p>
            <button
              type="button"
              onClick={() => void loadDetail(tenant.slug)}
              className="mt-3 min-h-11 rounded border border-[var(--line)] px-3 text-xs font-medium"
            >
              Lihat detail
            </button>
          </li>
        ))}
      </ul>

      {selected ? (
        <section
          aria-labelledby="tenant-detail-title"
          className="rounded-[10px] border border-[var(--line)] bg-white p-5"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 id="tenant-detail-title" className="text-base font-semibold">
                Detail tenant
              </h2>
              <p className="mt-0.5 text-xs text-[var(--muted)]">{selected}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setDetail(null);
              }}
              className="min-h-9 rounded border border-[var(--line)] px-2.5 text-xs"
            >
              Tutup
            </button>
          </div>

          {detailLoading ? (
            <p className="mt-4 text-sm text-[var(--ink-2)]">Memuat detail…</p>
          ) : detail ? (
            <div className="mt-4 space-y-4">
              <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-xs text-[var(--muted)]">Status</dt>
                  <dd className="mt-1"><OpsStatus status={detail.status} /></dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--muted)]">Anggota</dt>
                  <dd className="mt-1 font-medium">{detail.members}</dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--muted)]">Job aktif</dt>
                  <dd className="mt-1 font-medium">{detail.queued_jobs}</dd>
                </div>
                <div>
                  <dt className="text-xs text-[var(--muted)]">Job gagal/berhenti</dt>
                  <dd className="mt-1 font-medium">{detail.failed_jobs}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-[var(--muted)]">Owner</dt>
                  <dd className="mt-1 break-words font-medium">
                    {detail.owner_email ?? "—"}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-[var(--muted)]">Terakhir diubah</dt>
                  <dd className="mt-1">{formatDateTime(detail.updated_at)}</dd>
                </div>
              </dl>

              {detail.failure_note ? (
                <p className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-3 py-2 text-sm text-[var(--danger)]">
                  {detail.failure_note}
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2 border-t border-[var(--line)] pt-4">
                {detail.status === "active" ? (
                  confirmSuspend ? (
                    <>
                      <button
                        type="button"
                        onClick={() => void changeStatus(detail.slug, "suspend")}
                        disabled={pending !== null}
                        className="min-h-11 rounded-md bg-[var(--danger)] px-4 text-sm font-semibold text-white disabled:opacity-60"
                      >
                        {pending === "suspend" ? "Menangguhkan…" : "Ya, tangguhkan"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmSuspend(false)}
                        className="min-h-11 rounded-md border border-[var(--line)] px-4 text-sm"
                      >
                        Batal
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmSuspend(true)}
                      className="min-h-11 rounded-md border border-[#f0c9cb] px-4 text-sm font-semibold text-[var(--danger)] hover:bg-[#fdf0f0]"
                    >
                      Tangguhkan tenant
                    </button>
                  )
                ) : detail.status === "suspended" ? (
                  <button
                    type="button"
                    onClick={() => void changeStatus(detail.slug, "resume")}
                    disabled={pending !== null}
                    className="min-h-11 rounded-md bg-[var(--brand)] px-4 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    {pending === "resume" ? "Mengaktifkan…" : "Aktifkan kembali"}
                  </button>
                ) : null}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}