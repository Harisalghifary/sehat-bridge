import type { Metadata } from "next";
import Link from "next/link";

import { SectionHeading } from "@/components/site/SectionHeading";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privasi",
  description:
    "Kebijakan privasi Sehat Bridge: data kontak yang dikumpulkan dari formulir demo, cookie sesi, masa simpan 12 bulan, dan cara meminta penghapusan.",
  alternates: { canonical: "/privasi" },
  openGraph: {
    title: "Kebijakan privasi Sehat Bridge",
    description:
      "Apa yang kami kumpulkan, mengapa, berapa lama, dan bagaimana meminta penghapusan.",
    url: "/privasi",
  },
};

export default function PrivasiPage() {
  return (
    <>
      <section className="border-b border-[var(--line)]">
        <div className="container-site py-16 sm:py-20">
          <SectionHeading
            as="h1"
            eyebrow="Privasi"
            title="Kebijakan privasi dalam bahasa sehari-hari"
            description="Terakhir diperbarui: 4 November 2026. Halaman ini menjelaskan data yang benar-benar kami proses pada versi 0.1.0."
          />
        </div>
      </section>

      <section className="container-site py-14 sm:py-16">
        <div className="prose-site mx-auto max-w-3xl">
          <h2>Data yang kami kumpulkan</h2>
          <p>
            Saat Anda mengirim formulir demo, kami menerima nama, email, nama
            faskes, jenis faskes, kota, nomor telepon (opsional), dan pesan
            (opsional). Kami juga mencatat alamat IP dan user-agent untuk
            mencegah penyalahgunaan formulir.
          </p>
          <p>
            Situs ini tidak memasang cookie iklan atau pelacak pihak ketiga.
            Cookie yang dipakai adalah cookie sesi teknis untuk aplikasi faskes
            ketika Anda masuk; halaman pemasaran dapat dibaca tanpa cookie.
          </p>

          <h2>Mengapa data itu diproses</h2>
          <ul>
            <li>Menjawab permintaan demo dan pertanyaan yang Anda kirim.</li>
            <li>
              Menjaga formulir dari spam dan pengiriman otomatis, termasuk
              pembatasan laju per alamat IP.
            </li>
            <li>
              Memenuhi kewajiban keamanan dasar, seperti mencatat peristiwa
              perubahan peran pada aplikasi.
            </li>
          </ul>

          <h2>Berapa lama disimpan</h2>
          <p>
            Data lead disimpan maksimal 12 bulan sejak kontak terakhir, lalu
            dihapus atau dianonimkan. Data audit aplikasi disimpan lebih lama
            karena kebutuhan investigasi keamanan, tetapi tidak memuat isi
            berkas atau secret integrasi.
          </p>

          <h2>Data pasien</h2>
          <p>
            Versi 0.1.0 tidak menyimpan nama pasien, NIK, atau data klinis.
            Sinkronisasi pasien yang ditunjukkan dalam demo memakai identifier
            sintetis. Jangan mengirim data pasien melalui formulir demo.
          </p>

          <h2>Pembagian data</h2>
          <p>
            Kami tidak menjual data kontak. Data hanya diakses oleh tim yang
            menindaklanjuti permintaan demo atau memelihara layanan. Penyedia
            infrastruktur yang digunakan untuk menjalankan situs ini memproses
            data sebagai operator teknis.
          </p>

          <h2>Hak Anda</h2>
          <p>
            Anda dapat meminta salinan, koreksi, atau penghapusan data kontak
            dengan mengirim email ke{" "}
            <a href={`mailto:${site.email}`}>{site.email}</a>. Sertakan alamat
            email yang Anda pakai saat mengirim formulir agar kami dapat
            menemukan catatannya. Kami menanggapi dalam waktu yang wajar.
          </p>

          <h2>Keamanan</h2>
          <p>
            Data aplikasi dipisahkan per faskes menggunakan schema dan
            row-level security. Kredensial integrasi disimpan terenkripsi dan
            tidak pernah dikembalikan melalui API. Meski begitu, tidak ada sistem
            yang bisa menjamin keamanan mutlak; kami akan memberi tahu pengguna
            jika terjadi insiden yang berdampak pada data mereka.
          </p>

          <h2>Perubahan kebijakan</h2>
          <p>
            Jika kebijakan ini berubah secara material, tanggal pembaruan di atas
            akan berubah dan perubahan akan dijelaskan di halaman ini. Pertanyaan
            dapat dikirim ke{" "}
            <a href={`mailto:${site.email}`}>{site.email}</a> atau melalui{" "}
            <Link href="/demo">formulir demo</Link>.
          </p>

          <h2>Disclaimer</h2>
          <p>{site.disclaimer}</p>
        </div>
      </section>
    </>
  );
}