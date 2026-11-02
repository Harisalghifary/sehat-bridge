import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Sehat Bridge",
    template: "%s · Sehat Bridge",
  },
  description:
    "Platform multi-tenant untuk faskes Indonesia: berkas, anggota, dan integrasi SATUSEHAT dalam satu alur.",
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:8080"),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="min-h-dvh bg-white text-[var(--ink)] antialiased">{children}</body>
    </html>
  );
}