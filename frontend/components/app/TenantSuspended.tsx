"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function TenantSuspended({ tenant }: { tenant?: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function signOut() {
    setPending(true);
    try {
      await fetch("/api/session", { method: "DELETE" });
    } finally {
      router.replace("/masuk");
      router.refresh();
    }
  }

  return (
    <div className="grid min-h-dvh place-items-center bg-[var(--bg-alt)] px-4">
      <div className="max-w-lg rounded-[10px] border border-[#f0dfbc] bg-white p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--warn)]">
          Akses ditangguhkan
        </p>
        <h1 className="h2 mt-3">Faskes ini sedang dinonaktifkan</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
          {tenant ? (
            <>
              Tenant <span className="font-mono font-medium">{tenant}</span>{" "}
              ditangguhkan oleh operator platform.
            </>
          ) : (
            "Faskes Anda ditangguhkan oleh operator platform."
          )}{" "}
          Data tidak dihapus, tetapi login dan API tenant diblokir sampai status
          diaktifkan kembali.
        </p>
        <p className="mt-3 text-sm leading-6 text-[var(--ink-2)]">
          Hubungi operator platform bila ini tidak sesuai. Anda dapat keluar dari
          sesi ini sekarang.
        </p>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link
            href="/app/dasbor"
            className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-5 text-sm font-semibold"
          >
            Coba lagi
          </Link>
          <button
            type="button"
            onClick={() => void signOut()}
            disabled={pending}
            className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white disabled:opacity-70"
          >
            {pending ? "Keluar…" : "Keluar dari sesi"}
          </button>
        </div>
      </div>
    </div>
  );
}