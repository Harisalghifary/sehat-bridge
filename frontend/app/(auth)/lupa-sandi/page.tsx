import type { Metadata } from "next";
import Link from "next/link";

import { PasswordResetRequestForm } from "@/components/auth/PasswordResetForms";

export const metadata: Metadata = {
  title: "Lupa kata sandi",
  description: "Minta tautan pengaturan ulang kata sandi melalui email.",
  robots: { index: false, follow: false },
};

export default function LupaSandiPage() {
  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Pemulihan akses
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Lupa kata sandi
      </h1>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
        Masukkan email akun Anda. Bila alamat itu terdaftar, kami mengirim tautan
        untuk membuat kata sandi baru. Tautan berlaku 60 menit dan hanya bisa
        dipakai sekali.
      </p>
      <div className="mt-6">
        <PasswordResetRequestForm />
      </div>
      <p className="mt-6 border-t border-[var(--line)] pt-5 text-sm">
        <Link href="/masuk" className="text-[var(--brand)] underline underline-offset-4">
          Kembali ke halaman masuk
        </Link>
      </p>
    </div>
  );
}