import Link from "next/link";

export function AccessDenied() {
  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-white p-8">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
        403
      </p>
      <h1 className="h2 mt-3">Halaman ini khusus owner dan admin</h1>
      <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--ink-2)]">
        Peran Anda tidak memiliki akses ke bagian ini. Menu terkait juga
        disembunyikan, dan API tetap menolak permintaan langsung dengan status
        403.
      </p>
      <Link
        href="/app/dasbor"
        className="mt-6 inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white"
      >
        Kembali ke dasbor
      </Link>
    </div>
  );
}