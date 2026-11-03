import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-plus-jakarta",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:8080",
  ),
  title: {
    default: "Sehat Bridge — platform berkas dan integrasi faskes",
    template: "%s · Sehat Bridge",
  },
  description:
    "Platform multi-tenant untuk faskes Indonesia: berkas, anggota, peran, dan integrasi SATUSEHAT dalam satu alur. Mode uji, tanpa data pasien.",
  applicationName: "Sehat Bridge",
  openGraph: {
    type: "website",
    locale: "id_ID",
    siteName: "Sehat Bridge",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className={plusJakarta.variable}>
      <body className="min-h-dvh bg-white font-sans text-[var(--ink)] antialiased">
        {children}
      </body>
    </html>
  );
}