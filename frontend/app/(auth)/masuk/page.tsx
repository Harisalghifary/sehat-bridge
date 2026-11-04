import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/LoginForm";
import { readSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "Masuk",
  description: "Masuk ke aplikasi faskes Sehat Bridge.",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function MasukPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const session = await readSession();
  if (session) redirect("/app/dasbor");

  const params = await searchParams;
  const next =
    params.next && params.next.startsWith("/app") ? params.next : "/app/dasbor";

  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-6 sm:p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Aplikasi faskes
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight">Masuk</h1>
      <p className="mt-2 text-sm leading-6 text-[var(--ink-2)]">
        Gunakan kode faskes dan akun yang diberikan admin. Sesi disimpan di
        server; token tidak pernah dikirim ke browser.
      </p>

      <div className="mt-7">
        <LoginForm next={next} />
      </div>

      <div className="mt-6 flex flex-col gap-2 border-t border-[var(--line)] pt-5 text-sm">
        <Link
          href="/lupa-sandi"
          className="text-[var(--brand)] underline underline-offset-4"
        >
          Lupa kata sandi?
        </Link>
        <Link
          href="/daftar"
          className="text-[var(--ink-2)] underline underline-offset-4"
        >
          Belum punya akses?
        </Link>
      </div>
    </div>
  );
}