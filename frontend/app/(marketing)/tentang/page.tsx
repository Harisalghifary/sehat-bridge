import type { Metadata } from "next";

import { ButtonLink } from "@/components/site/ButtonLink";
import { SectionHeading } from "@/components/site/SectionHeading";
import { site, whatsappHref } from "@/lib/site";

export const metadata: Metadata = {
  title: "Tentang",
  description:
    "Sehat Bridge adalah proyek independen yang membangun platform administrasi faskes. Baca cerita, prinsip, dan status tim secara terbuka.",
  alternates: { canonical: "/tentang" },
  openGraph: {
    title: "Tentang Sehat Bridge",
    description:
      "Proyek independen untuk administrasi faskes Indonesia. Tidak berafiliasi dengan Kemenkes.",
    url: "/tentang",
  },
};

export default function TentangPage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            as="h1"
            eyebrow="Tentang"
            title="Dibangun dengan jarak yang jujur dari klaim besar"
            description="Sehat Bridge lahir dari satu pengamatan sederhana: banyak faskes kecil sudah punya data, tetapi belum punya alur yang membuat data itu bisa ditemukan dan dipercaya."
          />
        </div>
      </section>

      <section className="container-site grid gap-12 py-16 sm:py-20 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="prose-site max-w-2xl">
          <h2>Cerita</h2>
          <p>
            Pekerjaan administrasi di faskes sering berjalan di beberapa tempat
            sekaligus: grup pesan untuk berkas, spreadsheet untuk staf, dan
            aplikasi lain untuk integrasi. Ketika seseorang bertanya “versi mana
            yang terbaru?”, jawabannya bergantung pada siapa yang ditanya.
          </p>
          <p>
            Sehat Bridge mencoba merapikan bagian itu tanpa mengklaim menggantikan
            rekam medis elektronik. Fokusnya adalah lapisan operasional: berkas,
            anggota, peran, kuota, dan pipa integrasi. Data klinis dan data pasien
            nyata sengaja tidak disimpan pada versi ini.
          </p>
          <p>
            Integrasi SATUSEHAT dibangun dengan adapter mock karena akses produksi
            memerlukan badan hukum dan onboarding faskes. Kami memilih
            mempublikasikan batas itu daripada menampilkan logo yang belum bisa
            dipertanggungjawabkan.
          </p>

          <h2>Yang kami percaya</h2>
          <ul>
            <li>
              Isolasi data harus bisa dijelaskan secara teknis, bukan hanya lewat
              kalimat pemasaran.
            </li>
            <li>
              Fitur yang belum siap sebaiknya diberi label “direncanakan”, bukan
              “segera hadir” tanpa tanggal.
            </li>
            <li>
              Rahasia pelanggan tidak boleh muncul di respons API, log, atau
              metadata audit.
            </li>
            <li>
              Demo yang baik menunjukkan alur dan batasnya, termasuk hal yang belum
              selesai.
            </li>
          </ul>
        </div>

        <aside className="h-fit space-y-4">
          <div className="rounded-[10px] border border-[var(--line)] bg-white p-6">
            <h2 className="h3">Kontak</h2>
            <dl className="mt-4 space-y-3 text-sm">
              <div>
                <dt className="text-[var(--muted)]">Email</dt>
                <dd>
                  <a
                    className="underline underline-offset-4"
                    href={`mailto:${site.email}`}
                  >
                    {site.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-[var(--muted)]">WhatsApp</dt>
                <dd>
                  <a
                    className="underline underline-offset-4"
                    href={whatsappHref}
                    rel="noreferrer"
                    target="_blank"
                  >
                    {site.whatsappDisplay}
                  </a>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    Placeholder demo; diganti sebelum peluncuran.
                  </p>
                </dd>
              </div>
              <div>
                <dt className="text-[var(--muted)]">Lokasi</dt>
                <dd>{site.location}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-[10px] border border-[var(--line)] bg-[var(--bg-alt)] p-6">
            <h2 className="h3">Disclaimer</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              {site.disclaimer} Nama SATUSEHAT merujuk pada program resmi
              Kemenkes; penyebutan ini tidak menyiratkan afiliasi atau dukungan.
            </p>
          </div>
        </aside>
      </section>

      <section className="border-y border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            eyebrow="Tim"
            title="Peran yang sedang diisi"
            description="Kami tidak menampilkan foto atau nama fiktif. Bagian ini akan diperbarui ketika posisi benar-benar terisi."
          />
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {[
              ["Produk & riset faskes", "Posisi belum diisi"],
              ["Rekayasa platform", "Posisi belum diisi"],
              ["Kepatuhan & privasi", "Posisi belum diisi"],
            ].map(([role, status]) => (
              <div
                key={role}
                className="rounded-[10px] border border-dashed border-[var(--line)] bg-white p-6"
              >
                <p className="text-sm font-semibold">{role}</p>
                <p className="mt-2 text-xs uppercase tracking-wide text-[var(--muted)]">
                  {status}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-8">
            <ButtonLink href="/demo" variant="secondary">
              Hubungi kami
            </ButtonLink>
          </div>
        </div>
      </section>
    </>
  );
}