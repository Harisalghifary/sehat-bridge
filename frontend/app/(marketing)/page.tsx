import type { Metadata } from "next";
import Link from "next/link";

import { AppPreview } from "@/components/site/AppPreview";
import { ButtonLink } from "@/components/site/ButtonLink";
import { SectionHeading } from "@/components/site/SectionHeading";
import { StatusChip } from "@/components/site/StatusChip";
import { site, whatsappHref } from "@/lib/site";

export const metadata: Metadata = {
  title: {
    absolute: "Sehat Bridge — berkas, anggota, dan integrasi faskes",
  },
  description:
    "Rapikan berkas, kelola anggota, dan siapkan integrasi SATUSEHAT untuk klinik, laboratorium, dan praktik mandiri. Mode uji, isolasi data per faskes, tanpa data pasien.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Sehat Bridge — satu alur untuk faskes",
    description:
      "Berkas, anggota, peran, kuota, dan integrasi SATUSEHAT dalam satu aplikasi. Mode uji dan transparan.",
    url: "/",
  },
};

const problems = [
  {
    title: "Data tersebar",
    body: "Berkas ada di grup pesan, spreadsheet, dan komputer masing-masing staf. Menemukan versi terbaru memakan waktu.",
  },
  {
    title: "Integrasi manual",
    body: "Data organisasi dan pasien diketik ulang ke sistem lain. Setiap pengetikan ulang adalah peluang salah.",
  },
  {
    title: "Laporan terlambat",
    body: "Tanpa jejak aktivitas, sulit mengetahui siapa mengubah apa dan kapan, apalagi saat audit internal.",
  },
];

const steps = [
  {
    title: "Daftar faskes",
    body: "Satu tenant untuk satu faskes. Owner mengundang admin dan staf sesuai peran.",
  },
  {
    title: "Unggah berkas",
    body: "Berkas masuk ke ruang penyimpanan tenant dengan batas ukuran, tipe, dan kuota.",
  },
  {
    title: "Hubungkan SATUSEHAT",
    body: "Simpan kredensial terenkripsi, uji koneksi, lalu antrekan sinkronisasi organisasi.",
  },
  {
    title: "Pantau sinkronisasi",
    body: "Lihat status job, percobaan ulang, dan pemetaan ID tanpa membuka terminal.",
  },
];

const modules = [
  {
    title: "Berkas",
    body: "Unggah langsung ke object storage dengan batas 25 MB per berkas dan kuota 1 GB per faskes.",
    audience: "Admin dan staf",
  },
  {
    title: "Anggota & peran",
    body: "Owner, admin, dan member dengan aturan server-side, termasuk perlindungan owner terakhir.",
    audience: "Owner",
  },
  {
    title: "Integrasi",
    body: "Kredensial SATUSEHAT per tenant, tes koneksi, antrean sinkronisasi, dan riwayat job.",
    audience: "Owner dan admin",
  },
  {
    title: "Audit",
    body: "Perubahan peran, unggahan selesai, dan hasil sinkronisasi tercatat sebagai peristiwa.",
    audience: "Owner",
  },
  {
    title: "Kuota",
    body: "Penyimpanan dihitung per tenant. Sisa kuota terlihat sebelum unggahan berikutnya.",
    audience: "Owner dan admin",
  },
  {
    title: "Keamanan tenant",
    body: "Schema terpisah dan row-level security sebagai lapisan kedua, bukan sekadar filter aplikasi.",
    audience: "Semua peran",
  },
];

const limits = [
  ["25 MB", "Ukuran maksimum per berkas"],
  ["1 GB", "Kuota penyimpanan per faskes"],
  ["5", "Percobaan sinkronisasi sebelum dead-letter"],
];

export default function HomePage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site grid items-center gap-12 py-16 sm:py-20 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
              Untuk klinik, lab, dan praktik mandiri
            </p>
            <h1 className="display mt-4">
              Satu alur untuk berkas, anggota, dan{" "}
              <span className="italic text-[var(--brand)]">integrasi faskes</span>.
            </h1>
            <p className="lead mt-6">
              Sehat Bridge menyatukan dokumen operasional, pengelolaan staf, dan
              persiapan koneksi SATUSEHAT dalam satu aplikasi. Setiap faskes
              mendapat ruang data sendiri — bukan folder bersama yang rawan
              tertukar.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <ButtonLink href="/demo">Jadwalkan demo</ButtonLink>
              <ButtonLink href="/solusi" variant="secondary">
                Lihat solusi
              </ButtonLink>
            </div>
            <p className="mt-5 text-xs text-[var(--muted)]">
              Mode uji · tanpa data pasien · dapat dijalankan lokal
            </p>
          </div>
          <AppPreview variant="dashboard" />
        </div>
      </section>

      <section className="border-b border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site py-8">
          <div className="grid gap-6 md:grid-cols-[1.1fr_repeat(3,1fr)] md:items-center">
            <p className="text-sm font-semibold">
              Dibangun untuk alur kerja faskes Indonesia
            </p>
            <ul className="grid gap-3 text-sm text-[var(--ink-2)] sm:grid-cols-3 md:col-span-3 md:grid-cols-3">
              <li className="flex gap-2">
                <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
                Schema terpisah per tenant
              </li>
              <li className="flex gap-2">
                <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
                Peran diperiksa di server
              </li>
              <li className="flex gap-2">
                <span aria-hidden="true" className="mt-2 size-1.5 shrink-0 rounded-full bg-[var(--brand)]" />
                Riwayat audit untuk perubahan penting
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section className="container-site py-20 sm:py-24">
        <SectionHeading
          eyebrow="Masalah sehari-hari"
          title="Pekerjaan administrasi yang seharusnya tidak menyita waktu"
          description="Tiga hal yang paling sering muncul saat faskes mulai menata operasional digitalnya."
        />
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {problems.map((item, index) => (
            <article
              key={item.title}
              className="rounded-[10px] border border-[var(--line)] bg-white p-6"
            >
              <span className="text-xs font-semibold text-[var(--muted)]">
                0{index + 1}
              </span>
              <h3 className="h3 mt-3">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
                {item.body}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site py-20 sm:py-24">
          <SectionHeading
            eyebrow="Alur kerja"
            title="Dari pendaftaran sampai sinkronisasi, empat langkah"
            description="Tidak ada langkah tersembunyi. Setiap tahap punya status yang bisa diperiksa."
          />
          <ol className="mt-10 grid gap-6 md:grid-cols-4">
            {steps.map((step, index) => (
              <li key={step.title} className="relative">
                <div className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-full bg-white text-sm font-semibold ring-1 ring-[var(--line)]">
                    {index + 1}
                  </span>
                  <span
                    aria-hidden="true"
                    className="hidden h-px flex-1 bg-[var(--line)] md:block"
                  />
                </div>
                <h3 className="h3 mt-4">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="container-site py-20 sm:py-24">
        <SectionHeading
          eyebrow="Modul"
          title="Enam bagian yang bekerja bersama"
          description="Bukan daftar fitur yang tersebar. Modul berbagi tenancy, peran, dan audit yang sama."
        />
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => (
            <article
              key={module.title}
              className="rounded-[10px] border border-[var(--line)] bg-white p-6"
            >
              <h3 className="h3">{module.title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
                {module.body}
              </p>
              <p className="mt-4 text-xs font-medium text-[var(--muted)]">
                Untuk: {module.audience}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site grid items-center gap-10 py-20 sm:py-24 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <SectionHeading
              eyebrow="Tampilan produk"
              title="Berkas yang bisa ditemukan lagi"
              description="Daftar berkas menunjukkan nama, status, pengunggah, dan waktu. Batas tipe serta ukuran terlihat sebelum unggah, bukan setelah gagal."
            />
            <div className="mt-6">
              <ButtonLink href="/demo" variant="secondary">
                Minta tur produk
              </ButtonLink>
            </div>
          </div>
          <AppPreview variant="files" />
        </div>
      </section>

      <section className="bg-[var(--ink)] text-white">
        <div className="container-site py-20 sm:py-24">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#9fd7d3]">
              Integrasi
            </p>
            <h2 className="h2 mt-3 text-white">
              Jujur soal status, bukan sekadar logo
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-[#c9d6dc]">
              SATUSEHAT produksi memerlukan badan hukum dan onboarding faskes.
              Karena itu pipeline dibangun dengan adapter mock yang bisa diuji
              hari ini, dan adapter live yang hanya diaktifkan lewat konfigurasi.
            </p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            <div className="rounded-[10px] border border-white/15 bg-white/5 p-6">
              <StatusChip tone="test">Mode uji</StatusChip>
              <h3 className="h3 mt-4 text-white">SATUSEHAT</h3>
              <p className="mt-2 text-sm leading-6 text-[#c9d6dc]">
                Token, organisasi, antrean, dan retry sudah berjalan. Akses
                produksi menunggu proses resmi.
              </p>
            </div>
            <div className="rounded-[10px] border border-white/15 bg-white/5 p-6">
              <StatusChip tone="planned">Direncanakan</StatusChip>
              <h3 className="h3 mt-4 text-white">BPJS</h3>
              <p className="mt-2 text-sm leading-6 text-[#c9d6dc]">
                Belum ada koneksi. Modul ini tidak ditampilkan sebagai fitur
                yang siap dipakai.
              </p>
            </div>
            <div className="rounded-[10px] border border-white/15 bg-white/5 p-6">
              <StatusChip tone="planned">Direncanakan</StatusChip>
              <h3 className="h3 mt-4 text-white">LIS/RIS</h3>
              <p className="mt-2 text-sm leading-6 text-[#c9d6dc]">
                Integrasi laboratorium dan radiologi masih dalam perencanaan,
                tanpa tanggal yang dijanjikan.
              </p>
            </div>
          </div>
          <div className="mt-8">
            <Link
              href="/integrasi"
              className="text-sm font-semibold text-white underline underline-offset-4"
            >
              Baca detail status integrasi
            </Link>
          </div>
        </div>
      </section>

      <section className="container-site py-20 sm:py-24">
        <SectionHeading
          eyebrow="Keamanan"
          title="Isolasi data adalah fondasi, bukan tambahan"
          description="Keputusan arsitektur yang bisa diperiksa di repositori, bukan janji di halaman pemasaran."
        />
        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {[
            [
              "Satu schema per faskes",
              "Nama schema diturunkan dari slug tenant. Aplikasi memakai peran database non-owner agar RLS benar-benar berlaku.",
            ],
            [
              "Row-level security",
              "Kebijakan memeriksa identitas tenant dari transaksi, bukan header yang bisa dipalsukan klien.",
            ],
            [
              "Rahasia terenkripsi",
              "Kredensial integrasi disimpan sebagai ciphertext. Secret tidak pernah dikembalikan API atau masuk metadata audit.",
            ],
            [
              "Sesi berumur pendek",
              "Access token 15 menit dan refresh token berotasi, dengan deteksi pemakaian ulang.",
            ],
          ].map(([title, body]) => (
            <article key={title} className="border-l-2 border-[var(--brand)] pl-5">
              <h3 className="h3">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-[var(--line)] bg-[var(--bg-alt)]">
        <div className="container-site py-16 sm:py-20">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
              Batas versi 0.1.0
            </p>
            <h2 className="h2 mt-3">Angka yang bisa dipertanggungjawabkan</h2>
            <p className="mt-4 text-sm leading-6 text-[var(--ink-2)]">
              Ini batas produk yang berlaku sekarang, bukan klaim jumlah
              pelanggan atau hasil bisnis.
            </p>
          </div>
          <dl className="mt-10 grid gap-6 sm:grid-cols-3">
            {limits.map(([value, label]) => (
              <div key={label}>
                <dt className="text-sm text-[var(--ink-2)]">{label}</dt>
                <dd className="mt-2 text-4xl font-semibold tracking-tight">
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="container-site py-20 sm:py-24">
        <SectionHeading
          eyebrow="Implementasi"
          title="Tiga tahap, tanpa lompatan besar"
          description="Kami lebih memilih onboarding yang bisa dijelaskan daripada janji go-live instan."
        />
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            [
              "Penilaian",
              "Kami memetakan jenis faskes, jumlah staf, dan alur berkas yang sudah berjalan.",
            ],
            [
              "Penyiapan",
              "Tenant dibuat, peran disusun, dan kredensial integrasi diuji di mode mock.",
            ],
            [
              "Go-live terbatas",
              "Staf mulai memakai berkas dan anggota. Integrasi produksi mengikuti kesiapan resmi.",
            ],
          ].map(([title, body], index) => (
            <article
              key={title}
              className="rounded-[10px] border border-[var(--line)] bg-white p-6"
            >
              <span className="text-xs font-semibold text-[var(--muted)]">
                Tahap {index + 1}
              </span>
              <h3 className="h3 mt-3">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
                {body}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="bg-[var(--brand)] text-white">
        <div className="container-site flex flex-col gap-8 py-16 sm:py-20 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <h2 className="h2 text-white">
              Ingin melihat alurnya dengan data contoh?
            </h2>
            <p className="mt-4 text-base leading-7 text-white">
              Kami akan menunjukkan dasbor, unggahan berkas, dan antrean
              sinkronisasi SATUSEHAT dalam mode uji. Tidak perlu menyiapkan
              data pasien.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/demo"
              className="inline-flex min-h-11 items-center justify-center rounded-md bg-white px-5 py-3 text-sm font-semibold text-[var(--brand-ink)] hover:bg-[#eef7f5]"
            >
              Jadwalkan demo
            </Link>
            <a
              href={whatsappHref}
              rel="noreferrer"
              target="_blank"
              className="inline-flex min-h-11 items-center justify-center rounded-md border border-white/40 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10"
            >
              WhatsApp {site.whatsappDisplay}
            </a>
          </div>
        </div>
      </section>
    </>
  );
}