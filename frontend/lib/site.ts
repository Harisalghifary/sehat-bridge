export const site = {
  name: "Sehat Bridge",
  tagline: "Satu alur untuk berkas, anggota, dan integrasi faskes.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:8080",
  email: "halo@sehatbridge.dev",
  whatsappNumber: "6281200000000",
  whatsappDisplay: "+62 812-0000-0000",
  location: "Jakarta, Indonesia",
  disclaimer:
    "Sehat Bridge adalah proyek independen dan tidak berafiliasi dengan Kemenkes.",
} as const;

export const whatsappHref = `https://wa.me/${site.whatsappNumber}?text=${encodeURIComponent(
  "Halo, saya ingin menjadwalkan demo Sehat Bridge.",
)}`;

export const navItems = [
  { href: "/solusi", label: "Solusi" },
  { href: "/integrasi", label: "Integrasi" },
  { href: "/tentang", label: "Tentang" },
  { href: "/faq", label: "FAQ" },
] as const;

export const footerColumns = [
  {
    title: "Produk",
    links: [
      { href: "/solusi", label: "Solusi" },
      { href: "/integrasi", label: "Integrasi" },
      { href: "/demo", label: "Jadwalkan demo" },
    ],
  },
  {
    title: "Perusahaan",
    links: [
      { href: "/tentang", label: "Tentang" },
      { href: "/faq", label: "FAQ" },
      { href: "/privasi", label: "Privasi" },
    ],
  },
  {
    title: "Masuk",
    links: [
      { href: "/masuk", label: "Aplikasi faskes" },
      { href: "/demo", label: "Minta akses" },
    ],
  },
] as const;