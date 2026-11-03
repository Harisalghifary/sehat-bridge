import { ButtonLink } from "@/components/site/ButtonLink";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";

export default function NotFound() {
  return (
    <>
      <SiteNav />
      <main id="main" className="container-site flex min-h-[60vh] items-center py-20">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
            404
          </p>
          <h1 className="display mt-3">Halaman yang Anda cari tidak ada.</h1>
          <p className="lead mt-5">
            Tautan mungkin sudah berubah atau alamatnya salah ketik. Anda bisa
            kembali ke beranda atau langsung menjadwalkan demo.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/">Kembali ke beranda</ButtonLink>
            <ButtonLink href="/demo" variant="secondary">
              Jadwalkan demo
            </ButtonLink>
          </div>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}