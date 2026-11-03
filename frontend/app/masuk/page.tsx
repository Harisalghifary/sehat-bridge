import type { Metadata } from "next";

import { ButtonLink } from "@/components/site/ButtonLink";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";

export const metadata: Metadata = {
  title: "Masuk",
  description: "Akses aplikasi faskes Sehat Bridge.",
  robots: { index: false, follow: false },
};

export default function MasukPage() {
  return (
    <>
      <SiteNav />
      <main id="main" className="container-site py-16 sm:py-20">
        <div className="mx-auto max-w-[420px] rounded-[10px] border border-[var(--line)] bg-white p-8">
          <h1 className="text-2xl font-semibold tracking-tight">
            Aplikasi faskes
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
            Halaman masuk dan sesi faskes dibangun pada tahap aplikasi
            berikutnya. Untuk sekarang, akun demo hanya tersedia lewat sesi
            pengembangan lokal yang dijelaskan di repositori.
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <ButtonLink href="/demo">Jadwalkan demo</ButtonLink>
            <ButtonLink href="/" variant="secondary">
              Kembali ke beranda
            </ButtonLink>
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}