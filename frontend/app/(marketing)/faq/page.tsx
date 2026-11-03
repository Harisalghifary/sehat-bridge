import type { Metadata } from "next";
import Link from "next/link";

import { JsonLd } from "@/components/site/JsonLd";
import { SectionHeading } from "@/components/site/SectionHeading";

export const metadata: Metadata = {
  title: "FAQ",
  description:
    "Pertanyaan umum tentang Sehat Bridge: status SATUSEHAT, data pasien, keamanan tenant, harga, dan cara memulai demo.",
  alternates: { canonical: "/faq" },
  openGraph: {
    title: "FAQ Sehat Bridge",
    description:
      "Jawaban jujur soal SATUSEHAT mode uji, data, keamanan, dan demo.",
    url: "/faq",
  },
};

const faqs = [
  {
    question: "Apakah Sehat Bridge produk resmi Kemenkes?",
    answer:
      "Tidak. Sehat Bridge adalah proyek independen dan tidak berafiliasi dengan Kemenkes. Nama SATUSEHAT kami sebut sebagai program yang ingin diintegrasikan, bukan sebagai klaim kemitraan.",
  },
  {
    question: "Apakah versi ini sudah terhubung ke SATUSEHAT produksi?",
    answer:
      "Belum. Pipeline berjalan dengan adapter mock deterministik. Adapter live tersedia di kode dan hanya aktif lewat konfigurasi, tetapi memerlukan kredensial produksi yang belum kami miliki.",
  },
  {
    question: "Apakah data pasien disimpan?",
    answer:
      "Tidak. Versi 0.1.0 tidak menyimpan nama pasien, NIK, atau data klinis. Sinkronisasi pasien yang ada bersifat demo dengan identifier sintetis dan tidak memuat identitas nyata.",
  },
  {
    question: "Bagaimana data antar-faskes dipisahkan?",
    answer:
      "Setiap faskes mendapat schema database sendiri. Aplikasi memakai peran database non-owner sehingga row-level security benar-benar berlaku, dan identitas tenant berasal dari token yang terverifikasi, bukan header yang bisa dipalsukan.",
  },
  {
    question: "Berkas apa saja yang bisa diunggah?",
    answer:
      "PDF, PNG, JPEG, TXT, dan CSV dengan ukuran maksimum 25 MB per berkas. Kuota penyimpanan default adalah 1 GB per faskes.",
  },
  {
    question: "Apakah kredensial integrasi aman?",
    answer:
      "Client secret disimpan sebagai ciphertext menggunakan kunci terpisah dari kunci sesi. API hanya mengembalikan penanda bahwa secret ada, tidak pernah nilainya. Secret juga tidak ditulis ke log atau metadata audit.",
  },
  {
    question: "Siapa saja peran pengguna?",
    answer:
      "Owner, admin, dan member. Owner dapat mengelola peran; admin dapat mengelola operasional dan anggota non-owner; member memiliki akses terbatas. Owner terakhir tidak dapat diturunkan.",
  },
  {
    question: "Apakah ada integrasi BPJS atau LIS/RIS?",
    answer:
      "Belum. Keduanya berstatus direncanakan dan belum memiliki endpoint atau tanggal. Kami menampilkannya apa adanya agar tidak menimbulkan ekspektasi yang salah.",
  },
  {
    question: "Berapa biayanya?",
    answer:
      "Harga publik belum ditetapkan. Demo digunakan untuk memahami kebutuhan dan mengukur cakupan. Halaman ini tidak menampilkan angka yang belum bisa kami pertanggungjawabkan.",
  },
  {
    question: "Bagaimana cara mencoba?",
    answer:
      "Isi formulir demo. Kami akan mengatur sesi singkat dengan data contoh. Untuk pengembangan lokal, repositori menyediakan perintah Docker Compose dan akun demo.",
  },
  {
    question: "Apakah aplikasi bisa dipakai tanpa JavaScript?",
    answer:
      "Halaman pemasaran dirender sebagai HTML dan tetap terbaca tanpa JavaScript. Formulir demo memerlukan JavaScript untuk mengirim, dan aplikasi faskes memerlukan JavaScript seperti aplikasi web pada umumnya.",
  },
  {
    question: "Apakah Sehat Bridge menggantikan rekam medis elektronik?",
    answer:
      "Tidak. Fokus versi ini adalah lapisan operasional: berkas, anggota, peran, kuota, audit, dan pipa integrasi. Rekam medis adalah lingkup terpisah dengan kewajiban regulasi yang berbeda.",
  },
];

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map((item) => ({
    "@type": "Question",
    name: item.question,
    acceptedAnswer: { "@type": "Answer", text: item.answer },
  })),
};

export default function FaqPage() {
  return (
    <>
      <JsonLd data={faqJsonLd} />
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            as="h1"
            eyebrow="FAQ"
            title="Pertanyaan yang sering muncul"
            description="Jawaban di bawah menjelaskan apa yang sudah berjalan, apa yang belum, dan mengapa."
          />
        </div>
      </section>

      <section className="container-site py-14 sm:py-16">
        <div className="mx-auto max-w-3xl divide-y divide-[var(--line)] border-y border-[var(--line)]">
          {faqs.map((item, index) => (
            <details key={item.question} className="group py-2">
              <summary className="flex min-h-14 cursor-pointer items-center justify-between gap-4 py-3 text-left text-base font-medium marker:content-none">
                <span>
                  <span className="mr-2 text-xs font-semibold text-[var(--muted)]">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  {item.question}
                </span>
                <span
                  aria-hidden="true"
                  className="grid size-7 shrink-0 place-items-center rounded-full border border-[var(--line)] text-lg leading-none text-[var(--ink-2)] group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="pb-4 pl-8 pr-10 text-sm leading-7 text-[var(--ink-2)]">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
        <p className="mx-auto mt-8 max-w-3xl text-sm text-[var(--ink-2)]">
          Belum terjawab?{" "}
          <Link href="/demo" className="text-[var(--brand)] underline underline-offset-4">
            Kirim pertanyaan lewat formulir demo
          </Link>
          .
        </p>
      </section>
    </>
  );
}