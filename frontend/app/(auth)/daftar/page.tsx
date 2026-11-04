import type { Metadata } from "next";
import Link from "next/link";

import { ButtonLink } from "@/components/site/ButtonLink";

export const metadata: Metadata = {
  title: "Daftar",
  description:
    "Pendaftaran Sehat Bridge bersifat undangan. Minta admin faskes mengundang akun Anda.",
  robots: { index: false, follow: false },
};

export default function DaftarPage() {
  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Pendaftaran
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">
        Akses lewat undangan admin
      </h1>
      <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
        Pada versi ini, akun dibuat oleh admin faskes. Pendaftaran publik belum
        dibuka agar setiap anggota terhubung ke tenant yang benar dan perannya
        ditetapkan sejak awal.
      </p>
      <ol className="mt-5 space-y-3 text-sm leading-6 text-[var(--ink-2)]">
        <li>1. Hubungi admin faskes Anda dan minta akses.</li>
        <li>2. Admin menambahkan email Anda ke tenant yang sesuai.</li>
        <li>3. Masuk menggunakan kode faskes dan kata sandi yang diberikan.</li>
      </ol>
      <div className="mt-6 flex flex-col gap-3">
        <ButtonLink href="/masuk">Ke halaman masuk</ButtonLink>
        <ButtonLink href="/demo" variant="secondary">
          Belum punya faskes? Jadwalkan demo
        </ButtonLink>
      </div>
      <p className="mt-5 text-xs text-[var(--muted)]">
        Ingin tahu kebijakan data?{" "}
        <Link href="/privasi" className="underline underline-offset-4">
          Baca kebijakan privasi
        </Link>
        .
      </p>
    </div>
  );
}