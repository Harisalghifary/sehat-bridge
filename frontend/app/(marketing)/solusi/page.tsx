import type { Metadata } from "next";

import { AppPreview } from "@/components/site/AppPreview";
import { ButtonLink } from "@/components/site/ButtonLink";
import { SectionHeading } from "@/components/site/SectionHeading";
import { SolutionNav } from "@/components/site/SolutionNav";

export const metadata: Metadata = {
  title: "Solusi",
  description:
    "Modul Sehat Bridge untuk faskes: berkas, anggota dan peran, integrasi SATUSEHAT, serta audit. Lihat apa yang dikerjakan tiap bagian dan siapa penggunanya.",
  alternates: { canonical: "/solusi" },
  openGraph: {
    title: "Solusi Sehat Bridge",
    description:
      "Berkas, anggota, integrasi, dan audit dalam satu platform multi-tenant.",
    url: "/solusi",
  },
};

const sections = [
  {
    id: "berkas",
    eyebrow: "Berkas",
    title: "Satu tempat untuk dokumen operasional",
    body: "Unggah dokumen langsung ke penyimpanan objek tanpa melewati server aplikasi. Setiap berkas punya pemilik, tipe, ukuran, dan status yang jelas.",
    audience:
      "Admin mengunggah dan menghapus; staf membaca dokumen yang dibagikan.",
    bullets: [
      "Batas 25 MB per berkas dan kuota 1 GB per tenant.",
      "Tipe yang diterima: PDF, PNG, JPEG, TXT, dan CSV.",
      "Unduhan memakai tautan sementara, bukan URL publik permanen.",
    ],
    variant: "files" as const,
  },
  {
    id: "anggota",
    eyebrow: "Anggota & peran",
    title: "Peran yang tidak bisa dinaikkan sendiri",
    body: "Owner, admin, dan member dipisahkan di server. Perubahan peran dicatat, dan owner terakhir tidak dapat diturunkan.",
    audience:
      "Owner mengatur struktur tim; admin mengelola operasional harian.",
    bullets: [
      "Admin tidak dapat memberikan atau mengubah peran owner.",
      "Upaya menurunkan owner terakhir ditolak dengan pesan yang jelas.",
      "Anggota dari tenant lain tidak terlihat, termasuk lewat ID langsung.",
    ],
    variant: "members" as const,
  },
  {
    id: "integrasi",
    eyebrow: "Integrasi",
    title: "Pipeline yang bisa diuji sebelum akses produksi",
    body: "Kredensial SATUSEHAT disimpan terenkripsi per faskes. Tes koneksi, antrean job, percobaan ulang, dan pemetaan ID tersedia di satu layar.",
    audience:
      "Owner dan admin menyiapkan koneksi; operator melihat riwayat job.",
    bullets: [
      "Adapter mock sebagai default; adapter live hanya lewat konfigurasi.",
      "Kegagalan 5xx dicoba ulang dengan backoff, 4xx berhenti segera.",
      "Secret tidak pernah dikembalikan API atau ditulis ke log.",
    ],
    variant: "integration" as const,
  },
  {
    id: "audit",
    eyebrow: "Audit",
    title: "Jejak yang bisa dibaca manusia",
    body: "Peristiwa penting dicatat sebagai baris audit: perubahan peran, berkas selesai, hasil sinkronisasi, dan percobaan login.",
    audience:
      "Owner meninjau aktivitas; operator platform memakai filter saat investigasi.",
    bullets: [
      "Metadata tidak memuat secret atau isi berkas.",
      "Tenant ID ikut tercatat agar investigasi lintas faskes tidak menebak.",
      "Audit menjadi dasar untuk pertanyaan 'siapa mengubah apa'.",
    ],
    variant: "audit" as const,
  },
];

export default function SolusiPage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            as="h1"
            eyebrow="Solusi"
            title="Empat bagian, satu model data"
            description="Setiap modul memakai tenancy, autentikasi, dan audit yang sama. Tidak ada modul yang menyimpan salinan data anggota sendiri."
          />
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/demo">Jadwalkan demo</ButtonLink>
            <ButtonLink href="/integrasi" variant="secondary">
              Lihat status integrasi
            </ButtonLink>
          </div>
        </div>
      </section>

      <SolutionNav />

      {sections.map((section, index) => (
        <section
          key={section.id}
          id={section.id}
          aria-labelledby={`${section.id}-title`}
          className={`scroll-mt-28 border-b border-[var(--line)] ${
            index % 2 === 1 ? "bg-[var(--bg-alt)]" : ""
          }`}
        >
          <div className="container-site grid items-center gap-10 py-16 sm:py-20 lg:grid-cols-2">
            <div className={index % 2 === 1 ? "lg:order-2" : ""}>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
                {section.eyebrow}
              </p>
              <h2 id={`${section.id}-title`} className="h2 mt-3">
                {section.title}
              </h2>
              <p className="lead mt-4">{section.body}</p>
              <p className="mt-4 text-sm text-[var(--ink-2)]">
                <span className="font-semibold text-[var(--ink)]">
                  Siapa yang memakai:{" "}
                </span>
                {section.audience}
              </p>
              <ul className="mt-6 space-y-3">
                {section.bullets.map((bullet) => (
                  <li key={bullet} className="flex gap-3 text-sm leading-6">
                    <span
                      aria-hidden="true"
                      className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--brand)]"
                    />
                    <span className="text-[var(--ink-2)]">{bullet}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-7">
                <ButtonLink href="/demo" variant="secondary">
                  Lihat alurnya di demo
                </ButtonLink>
              </div>
            </div>
            <div className={index % 2 === 1 ? "lg:order-1" : ""}>
              <AppPreview variant={section.variant} />
            </div>
          </div>
        </section>
      ))}
    </>
  );
}