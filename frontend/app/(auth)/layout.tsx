import type { Metadata } from "next";
import Link from "next/link";

import { Logo } from "@/components/site/Logo";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Masuk",
  robots: { index: false, follow: false },
};

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-[var(--bg-alt)]">
      <header className="border-b border-[var(--line)] bg-white">
        <div className="container-site flex h-[72px] items-center justify-between">
          <Logo />
          <Link
            href="/"
            className="text-sm font-medium text-[var(--ink-2)] hover:text-[var(--ink)]"
          >
            Kembali ke situs
          </Link>
        </div>
      </header>
      <main id="main" className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-[420px]">{children}</div>
      </main>
      <footer className="container-site py-6 text-center text-xs text-[var(--muted)]">
        {site.disclaimer}
      </footer>
    </div>
  );
}