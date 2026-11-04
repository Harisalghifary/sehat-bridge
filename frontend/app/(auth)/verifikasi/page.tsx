import type { Metadata } from "next";

import { VerifyEmailPanel } from "@/components/auth/PasswordResetForms";

export const metadata: Metadata = {
  title: "Verifikasi email",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function VerifikasiPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Keamanan akun
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Verifikasi email
      </h1>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
        Kami memverifikasi tautan sekali pakai dari email Anda.
      </p>
      <div className="mt-6">
        <VerifyEmailPanel token={params.token ?? ""} />
      </div>
    </div>
  );
}