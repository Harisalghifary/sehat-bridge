import type { Metadata } from "next";

import { JsonLd } from "@/components/site/JsonLd";
import { SiteFooter } from "@/components/site/SiteFooter";
import { SiteNav } from "@/components/site/SiteNav";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  alternates: { canonical: "/" },
};

const organization = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: site.name,
  url: site.url,
  email: site.email,
  description:
    "Platform multi-tenant untuk fasilitas kesehatan Indonesia: berkas, anggota, peran, dan integrasi SATUSEHAT.",
  address: {
    "@type": "PostalAddress",
    addressLocality: "Jakarta",
    addressCountry: "ID",
  },
};

const application = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: site.name,
  applicationCategory: "BusinessApplication",
  operatingSystem: "Web",
  description:
    "Aplikasi faskes untuk mengelola berkas, anggota, peran, kuota, dan sinkronisasi SATUSEHAT dalam mode uji.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "IDR",
    description: "Akses demo terbatas untuk evaluasi.",
  },
};

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <a href="#main" className="skip-link">
        Lewati ke konten utama
      </a>
      <SiteNav />
      <main id="main">{children}</main>
      <SiteFooter />
      <JsonLd data={{ "@context": "https://schema.org", "@graph": [organization, application] }} />
    </>
  );
}