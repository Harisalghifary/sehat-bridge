import type { Metadata } from "next";

import { ButtonLink } from "@/components/site/ButtonLink";
import { SectionHeading } from "@/components/site/SectionHeading";
import { StatusChip } from "@/components/site/StatusChip";

export const metadata: Metadata = {
  title: "Integrasi",
  description:
    "Status nyata integrasi Sehat Bridge: SATUSEHAT dalam mode uji, BPJS dan LIS/RIS masih direncanakan. Penjelasan batasan akses produksi dan peran adapter mock.",
  alternates: { canonical: "/integrasi" },
  openGraph: {
    title: "Status integrasi Sehat Bridge",
    description:
      "SATUSEHAT mode uji, BPJS dan LIS/RIS direncanakan. Tanpa klaim yang belum terbukti.",
    url: "/integrasi",
  },
};

const integrations = [
  {
    name: "SATUSEHAT",
    tone: "test" as const,
    status: "Mode uji",
    headline: "Pipeline berjalan, akses produksi menunggu proses resmi",
    body: "Kami membangun adapter FHIR R4, antrean sinkronisasi, dan tes koneksi. Yang belum ada adalah kredensial produksi dari Kemenkes, karena itu memerlukan badan hukum dan onboarding faskes.",
    facts: [
      "Token dan pemanggilan FHIR diuji ke mock deterministik.",
      "Adapter live hanya dipilih lewat SATUSEHAT_MODE=live.",
      "Tidak ada data pasien nyata yang disimpan di versi ini.",
    ],
  },
  {
    name: "BPJS",
    tone: "planned" as const,
    status: "Direncanakan",
    headline: "Belum ada koneksi, belum ada tanggal",
    body: "Integrasi BPJS membutuhkan kerja sama dan spesifikasi akses tersendiri. Kami tidak menampilkan logo atau status 'segera hadir' untuk modul yang belum punya kontrak.",
    facts: [
      "Tidak ada endpoint, kredensial, atau job BPJS di kode saat ini.",
      "Permintaan fitur dicatat lewat formulir demo.",
    ],
  },
  {
    name: "LIS/RIS",
    tone: "planned" as const,
    status: "Direncanakan",
    headline: "Laboratorium dan radiologi masih dalam peta jalan",
    body: "Pertukaran hasil laboratorium dan radiologi butuh pemetaan format dan persetujuan vendor. Untuk sekarang, berkas hasil lab dapat diunggah sebagai PDF biasa.",
    facts: [
      "Belum ada koneksi langsung ke alat atau sistem LIS/RIS.",
      "Berkas hasil lab tetap bisa dikelola lewat modul Berkas.",
    ],
  },
];

export default function IntegrasiPage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            as="h1"
            eyebrow="Integrasi"
            title="Status apa adanya"
            description="Halaman ini membedakan tiga hal yang sering dicampur: pipeline yang sudah diuji, antarmuka yang direncanakan, dan akses produksi yang belum diberikan."
          />
        </div>
      </section>

      <section className="container-site py-16 sm:py-20">
        <div className="grid gap-5 lg:grid-cols-3">
          {integrations.map((integration) => (
            <article
              key={integration.name}
              className="flex flex-col rounded-[10px] border border-[var(--line)] bg-white p-6"
            >
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-xl font-semibold tracking-tight">
                  {integration.name}
                </h2>
                <StatusChip tone={integration.tone}>
                  {integration.status}
                </StatusChip>
              </div>
              <p className="mt-4 text-sm font-semibold leading-6">
                {integration.headline}
              </p>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
                {integration.body}
              </p>
              <ul className="mt-5 space-y-2 border-t border-[var(--line)] pt-5">
                {integration.facts.map((fact) => (
                  <li
                    key={fact}
                    className="flex gap-2 text-sm leading-6 text-[var(--ink-2)]"
                  >
                    <span
                      aria-hidden="true"
                      className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--muted)]"
                    />
                    {fact}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site grid gap-10 py-16 sm:py-20 lg:grid-cols-[1fr_1fr]">
          <div>
            <SectionHeading
              eyebrow="Mengapa mock dulu"
              title="Agar pekerjaan tidak menunggu izin"
              description="Akses SATUSEHAT produksi bukan sekadar mendaftar akun. Ada badan hukum, data faskes, dan perjanjian onboarding yang harus selesai."
            />
          </div>
          <div className="space-y-6 text-sm leading-7 text-[var(--ink-2)]">
            <p>
              Dengan adapter mock, tim dapat menguji alur kredensial, tes
              koneksi, antrean, percobaan ulang, dan pemetaan ID sejak awal.
              Ketika kredensial produksi tersedia, yang berubah adalah
              konfigurasi dan satu smoke test — bukan arsitektur aplikasi.
            </p>
            <p>
              Konsekuensinya juga jelas: mock tidak membuktikan validasi
              terminologi, batas laju, atau format error Kemenkes. Kami
              menuliskannya di dokumentasi teknis agar tidak ada klaim
              berlebihan.
            </p>
            <div className="rounded-[10px] border border-[var(--line)] bg-white p-5">
              <p className="text-sm font-semibold">Yang belum terbukti</p>
              <ul className="mt-3 space-y-2">
                <li>Validasi profil FHIR spesifik Kemenkes.</li>
                <li>Batas laju dan kuota API produksi.</li>
                <li>Kredensial dan jaringan produksi.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="container-site py-16 sm:py-20">
        <div className="flex flex-col gap-6 rounded-[10px] border border-[var(--line)] bg-white p-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="max-w-2xl">
            <h2 className="h2">Butuh integrasi yang belum ada di sini?</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
              Sampaikan lewat formulir demo. Kami memilih membangun berdasarkan
              kebutuhan nyata, bukan daftar logo.
            </p>
          </div>
          <ButtonLink href="/demo">Diskusikan kebutuhan</ButtonLink>
        </div>
      </section>
    </>
  );
}