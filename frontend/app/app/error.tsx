"use client";

import { TenantSuspended } from "@/components/app/TenantSuspended";
import { ButtonLink } from "@/components/site/ButtonLink";

export default function AppError({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  if (error.message === "Tenant is not active") {
    return <TenantSuspended />;
  }
  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        Aplikasi
      </p>
      <h1 className="h2 mt-3">Halaman gagal dimuat</h1>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--ink-2)]">
        Data mungkin sedang tidak tersedia. Sesi Anda tidak dihapus. Coba muat
        ulang; bila masalah berlanjut, kembali ke dasbor.
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={reset}
          className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white hover:bg-[var(--brand-ink)]"
        >
          Coba lagi
        </button>
        <ButtonLink href="/app/dasbor" variant="secondary">
          Ke dasbor
        </ButtonLink>
      </div>
    </div>
  );
}