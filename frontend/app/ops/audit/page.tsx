import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { OpsPage } from "@/components/ops/OpsPage";
import { ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { opsApiRequest, OpsSessionExpiredError } from "@/lib/ops-api";
import { readOpsSession } from "@/lib/ops-session";
import type { AuditList, OpsTenantList } from "@/lib/ops-types";

export const metadata: Metadata = {
  title: "Audit · Operator",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

const PAGE_SIZE = 50;

type Params = {
  tenant?: string;
  action?: string;
  from?: string;
  to?: string;
  offset?: string;
};

function toIso(date: string | undefined, end: boolean): string | undefined {
  if (!date) return undefined;
  const parsed = new Date(`${date}T00:00:00+07:00`);
  if (Number.isNaN(parsed.getTime())) return undefined;
  if (end) parsed.setDate(parsed.getDate() + 1);
  return parsed.toISOString();
}

export default async function OpsAuditPage({
  searchParams,
}: {
  searchParams: Promise<Params>;
}) {
  const session = await readOpsSession();
  if (!session) redirect("/ops/masuk?next=/ops/audit");

  const params = await searchParams;
  const offset = Math.max(0, Number.parseInt(params.offset ?? "0", 10) || 0);

  const query = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(offset),
  });
  if (params.tenant) query.set("tenant", params.tenant);
  if (params.action) query.set("action", params.action);
  const from = toIso(params.from, false);
  const to = toIso(params.to, true);
  if (from) query.set("created_from", from);
  if (to) query.set("created_to", to);

  try {
    const [audit, tenants, actions] = await Promise.all([
      opsApiRequest<AuditList>(session, `/admin/audit?${query.toString()}`),
      opsApiRequest<OpsTenantList>(session, "/admin/tenants"),
      opsApiRequest<string[]>(session, "/admin/audit/actions"),
    ]);

    const keep = new URLSearchParams();
    if (params.tenant) keep.set("tenant", params.tenant);
    if (params.action) keep.set("action", params.action);
    if (params.from) keep.set("from", params.from);
    if (params.to) keep.set("to", params.to);
    const prevHref = `/ops/audit?${new URLSearchParams({
      ...Object.fromEntries(keep),
      offset: String(Math.max(0, offset - PAGE_SIZE)),
    }).toString()}`;
    const nextOffset = offset + PAGE_SIZE;
    const nextHref = `/ops/audit?${new URLSearchParams({
      ...Object.fromEntries(keep),
      offset: String(nextOffset),
    }).toString()}`;

    return (
      <OpsPage next="/ops/audit">
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Audit</h1>
            <p className="mt-1 text-sm text-[var(--ink-2)]">
              Log lintas-tenant, hanya-baca. Filter berdasarkan tenant, aksi,
              atau rentang tanggal.
            </p>
          </div>

          <form
            method="get"
            action="/ops/audit"
            className="grid gap-3 rounded-[10px] border border-[var(--line)] bg-white p-4 sm:grid-cols-2 lg:grid-cols-5"
          >
            <div>
              <label htmlFor="audit-tenant" className="text-xs font-medium">
                Tenant
              </label>
              <select
                id="audit-tenant"
                name="tenant"
                defaultValue={params.tenant ?? ""}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-2 text-sm"
              >
                <option value="">Semua tenant</option>
                {tenants.items.map((tenant) => (
                  <option key={tenant.slug} value={tenant.slug}>
                    {tenant.name} ({tenant.slug})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="audit-action" className="text-xs font-medium">
                Aksi
              </label>
              <select
                id="audit-action"
                name="action"
                defaultValue={params.action ?? ""}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-2 text-sm"
              >
                <option value="">Semua aksi</option>
                {actions.map((action) => (
                  <option key={action} value={action}>
                    {action}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="audit-from" className="text-xs font-medium">
                Dari tanggal
              </label>
              <input
                id="audit-from"
                type="date"
                name="from"
                defaultValue={params.from ?? ""}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--line)] px-2 text-sm"
              />
            </div>
            <div>
              <label htmlFor="audit-to" className="text-xs font-medium">
                Sampai tanggal
              </label>
              <input
                id="audit-to"
                type="date"
                name="to"
                defaultValue={params.to ?? ""}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--line)] px-2 text-sm"
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                type="submit"
                className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-4 text-sm font-semibold text-white"
              >
                Terapkan
              </button>
              <Link
                href="/ops/audit"
                className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-3 text-sm"
              >
                Reset
              </Link>
            </div>
          </form>

          <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
            <p className="text-[var(--ink-2)]">
              {audit.total.toLocaleString("id-ID")} baris
              {audit.total > PAGE_SIZE
                ? ` · menampilkan ${offset + 1}–${Math.min(
                    offset + PAGE_SIZE,
                    audit.total,
                  )}`
                : ""}
            </p>
            <div className="flex gap-2">
              {offset > 0 ? (
                <Link
                  href={prevHref}
                  className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] bg-white px-3 text-sm font-medium"
                >
                  Sebelumnya
                </Link>
              ) : null}
              {nextOffset < audit.total ? (
                <Link
                  href={nextHref}
                  className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] bg-white px-3 text-sm font-medium"
                >
                  Berikutnya
                </Link>
              ) : null}
            </div>
          </div>

          {audit.items.length === 0 ? (
            <div className="rounded-[10px] border border-dashed border-[var(--line)] bg-white p-8 text-center">
              <p className="text-sm font-medium">Tidak ada baris audit.</p>
              <p className="mt-1 text-sm text-[var(--ink-2)]">
                Ubah filter atau jalankan tindakan terlebih dahulu.
              </p>
            </div>
          ) : (
            <>
              <div className="hidden overflow-hidden rounded-[10px] border border-[var(--line)] bg-white lg:block">
                <table className="w-full text-left text-sm">
                  <thead className="bg-[var(--bg-alt)] text-xs uppercase tracking-wide text-[var(--muted)]">
                    <tr>
                      <th scope="col" className="px-4 py-3 font-medium">Waktu</th>
                      <th scope="col" className="px-4 py-3 font-medium">Aksi</th>
                      <th scope="col" className="px-4 py-3 font-medium">Tenant</th>
                      <th scope="col" className="px-4 py-3 font-medium">Aktor</th>
                      <th scope="col" className="px-4 py-3 font-medium">Resource</th>
                      <th scope="col" className="px-4 py-3 font-medium">Metadata</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--line)]">
                    {audit.items.map((row) => (
                      <tr key={row.id}>
                        <td className="whitespace-nowrap px-4 py-3 text-[var(--ink-2)]">
                          {formatDateTime(row.created_at)}
                        </td>
                        <td className="px-4 py-3 font-medium">{row.action}</td>
                        <td className="px-4 py-3 text-[var(--ink-2)]">
                          {row.tenant_slug ?? "—"}
                        </td>
                        <td className="max-w-[200px] truncate px-4 py-3 text-[var(--ink-2)]">
                          {row.actor_email ?? "—"}
                        </td>
                        <td className="max-w-[180px] truncate px-4 py-3 text-[var(--ink-2)]">
                          {row.resource_type
                            ? `${row.resource_type}:${row.resource_id ?? "—"}`
                            : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {Object.keys(row.metadata).length ? (
                            <details>
                              <summary className="cursor-pointer text-xs font-medium text-[var(--brand)]">
                                Lihat
                              </summary>
                              <pre className="mt-1 max-w-[260px] overflow-auto whitespace-pre-wrap break-all rounded bg-[var(--bg-alt)] p-2 text-[11px]">
                                {JSON.stringify(row.metadata, null, 2)}
                              </pre>
                            </details>
                          ) : (
                            <span className="text-xs text-[var(--muted)]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <ul className="space-y-3 lg:hidden">
                {audit.items.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-[10px] border border-[var(--line)] bg-white p-4"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold">{row.action}</p>
                      <span className="text-xs text-[var(--muted)]">
                        {row.tenant_slug ?? "platform"}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      {formatDateTime(row.created_at)} · {row.actor_email ?? "—"}
                    </p>
                    {row.resource_type ? (
                      <p className="mt-1 break-all text-xs text-[var(--ink-2)]">
                        {row.resource_type}:{row.resource_id ?? "—"}
                      </p>
                    ) : null}
                    {Object.keys(row.metadata).length ? (
                      <details className="mt-2">
                        <summary className="min-h-9 cursor-pointer text-xs font-medium text-[var(--brand)]">
                          Metadata
                        </summary>
                        <pre className="mt-1 overflow-auto whitespace-pre-wrap break-all rounded bg-[var(--bg-alt)] p-2 text-[11px]">
                          {JSON.stringify(row.metadata, null, 2)}
                        </pre>
                      </details>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </OpsPage>
    );
  } catch (error) {
    if (error instanceof OpsSessionExpiredError) {
      redirect("/ops/masuk?next=/ops/audit");
    }
    if (error instanceof ApiError && error.status === 403) {
      redirect("/ops/masuk");
    }
    throw error;
  }
}