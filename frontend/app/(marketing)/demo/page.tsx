import type { Metadata } from "next";

import { DemoForm } from "@/components/site/DemoForm";
import { SectionHeading } from "@/components/site/SectionHeading";
import { site, whatsappHref } from "@/lib/site";

export const metadata: Metadata = {
  title: "Jadwalkan demo",
  description:
    "Minta demo Sehat Bridge untuk klinik, laboratorium, atau praktik mandiri. Kami menunjukkan berkas, anggota, dan antrean SATUSEHAT mode uji tanpa data pasien.",
  alternates: { canonical: "/demo" },
  openGraph: {
    title: "Jadwalkan demo Sehat Bridge",
    description:
      "Formulir singkat untuk melihat alur berkas, peran, dan integrasi mode uji.",
    url: "/demo",
  },
};

export default function DemoPage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-14 sm:py-16">
          <SectionHeading
            as="h1"
            eyebrow="Demo"
            title="Lihat alur kerja dengan data contoh"
            description="Isi formulir berikut. Kami akan menghubungi Anda untuk mengatur sesi singkat — biasanya 30 menit dan tanpa kewajiban teknis."
          />
        </div>
      </section>

      <section className="container-site grid gap-12 py-14 sm:py-16 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <h2 className="h2">Permintaan demo</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
            Kolom bertanda wajib diisi. Data kontak dipakai hanya untuk
            menindaklanjuti permintaan ini.
          </p>
          <div className="mt-8">
            <DemoForm />
          </div>
        </div>

        <aside
          aria-labelledby="demo-next"
          className="h-fit rounded-[10px] border border-[var(--line)] bg-[var(--bg-alt)] p-6 sm:p-8"
        >
          <h2 id="demo-next" className="h3">
            Apa yang terjadi setelah dikirim
          </h2>
          <ol className="mt-5 space-y-5">
            {[
              [
                "Kami membaca konteks",
                "Jenis faskes dan pertanyaan Anda menentukan skenario demo yang ditampilkan.",
              ],
              [
                "Waktu diusulkan",
                "Kami mengirim pilihan waktu dalam 1–2 hari kerja melalui email atau telepon.",
              ],
              [
                "Sesi 30 menit",
                "Dasbor, unggahan berkas, peran, dan antrean SATUSEHAT mode uji. Tidak ada instalasi.",
              ],
            ].map(([title, body], index) => (
              <li key={title} className="flex gap-3">
                <span className="grid size-7 shrink-0 place-items-center rounded-full bg-white text-xs font-semibold ring-1 ring-[var(--line)]">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-semibold">{title}</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--ink-2)]">
                    {body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-8 border-t border-[var(--line)] pt-5 text-sm">
            <p className="font-medium">Lebih suka lewat WhatsApp?</p>
            <a
              href={whatsappHref}
              rel="noreferrer"
              target="_blank"
              className="mt-1 inline-block text-[var(--brand)] underline underline-offset-4"
            >
              {site.whatsappDisplay}
            </a>
            <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
              Nomor ini adalah placeholder demo dan akan diganti sebelum
              peluncuran publik.
            </p>
          </div>
        </aside>
      </section>
    </>
  );
}