import type { Metadata } from "next";
import Link from "next/link";

import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Lupa kata sandi",
  description:
    "Pemulihan kata sandi Sehat Bridge dilakukan oleh admin faskes pada versi ini.",
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
        Pemulihan mandiri lewat email belum tersedia. Admin faskes dapat
        mereset kata sandi akun Anda dari pengelolaan anggota.
      </p>
      <div className="mt-5 rounded-md border border-[var(--line)] bg-[var(--bg-alt)] p-4 text-sm leading-6 text-[var(--ink-2)]">
        <p className="font-medium text-[var(--ink)]">Yang bisa Anda lakukan</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>Hubungi admin faskes dan minta reset kata sandi.</li>
          <li>Pastikan email akun Anda masih aktif.</li>
          <li>
            Jika admin tidak merespons, kirim email ke{" "}
            <a className="underline underline-offset-4" href={`mailto:${site.email}`}>
              {site.email}
            </a>
            .
          </li>
        </ul>
      </div>
      <div className="mt-6 flex flex-col gap-3">
        <Link
          href="/masuk"
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--brand-ink)]"
        >
          Kembali ke halaman masuk
        </Link>
      </div>
    </div>
  );
}