import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AppPage } from "@/components/app/AppPage";
import { PageHeader } from "@/components/app/PageHeader";
import { SignOutAll } from "@/components/app/SignOutAll";
import { apiRequest, SessionExpiredError } from "@/lib/api";
import { readSession } from "@/lib/session";
import type { MeResponse } from "@/lib/types";

export const metadata: Metadata = { title: "Pengaturan" };

export default async function SettingsPage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/pengaturan");

  try {
    const me = await apiRequest<MeResponse>(session, "/users/me");
    return (
      <AppPage next="/app/pengaturan">
      <div className="space-y-6">
        <PageHeader
          title="Pengaturan"
          description="Preferensi minimal untuk akun dan sesi Anda."
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
            <h2 className="text-sm font-semibold">Tampilan</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ink-2)]">Bahasa</dt>
                <dd className="font-medium">Indonesia</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ink-2)]">Zona waktu</dt>
                <dd className="font-medium">
                  {me.profile?.timezone ?? "UTC"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--ink-2)]">Faskes</dt>
                <dd className="font-medium">
                  {me.membership?.tenant.name ?? "—"}
                </dd>
              </div>
            </dl>
            <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
              Bahasa Inggris belum tersedia. Ubah zona waktu lewat halaman profil.
            </p>
            <Link
              href="/app/profil"
              className="mt-3 inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-4 text-sm font-semibold"
            >
              Buka profil
            </Link>
          </section>

          <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
            <h2 className="text-sm font-semibold">Sesi</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              Sesi disimpan di server dengan cookie httpOnly dan berlaku 30
              menit sejak aktivitas terakhir. Mengakhiri semua sesi juga
              mencabut refresh token di server.
            </p>
            <div className="mt-4">
              <SignOutAll />
            </div>
          </section>
        </div>
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/pengaturan");
    }
    throw error;
  }
}