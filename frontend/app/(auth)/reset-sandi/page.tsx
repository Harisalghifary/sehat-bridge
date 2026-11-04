import type { Metadata } from "next";

import { PasswordResetConfirmForm } from "@/components/auth/PasswordResetForms";

export const metadata: Metadata = {
  title: "Atur ulang kata sandi",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function ResetSandiPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>;
}) {
  const params = await searchParams;

  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Pemulihan akses
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Buat kata sandi baru
      </h1>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
        Setelah disimpan, semua sesi lama pada akun Anda dikeluarkan dan Anda
        masuk kembali dengan kata sandi baru.
      </p>
      <div className="mt-6">
        <PasswordResetConfirmForm token={params.token ?? ""} />
      </div>
    </div>
  );
}