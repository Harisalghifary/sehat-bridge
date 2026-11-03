"use client";

import { ButtonLink } from "@/components/site/ButtonLink";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <>
      <SiteNav />
      <main id="main" className="container-site flex min-h-[60vh] items-center py-20">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
            500
          </p>
          <h1 className="display mt-3">Terjadi kendala saat memuat halaman.</h1>
          <p className="lead mt-5">
            Kami sudah mencatat kejadian ini di log server. Silakan coba lagi;
            bila masih gagal, kembali ke beranda atau hubungi kami lewat
            formulir demo.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={reset}
              className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--brand-ink)]"
            >
              Coba lagi
            </button>
            <ButtonLink href="/demo" variant="secondary">
              Hubungi kami
            </ButtonLink>
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}