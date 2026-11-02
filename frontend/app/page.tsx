type Health = {
  status: string;
  version?: string;
};

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";

async function getHealth(): Promise<Health> {
  try {
    const response = await fetch(`${API_BASE_URL}/health/live`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return { status: "degraded" };
    }
    return (await response.json()) as Health;
  } catch {
    return { status: "unreachable" };
  }
}

export default async function Home() {
  const health = await getHealth();
  const healthy = health.status === "ok";

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col px-6 py-8 sm:px-8">
      <header className="flex items-center justify-between border-b border-[var(--line)] pb-6">
        <div className="flex items-center gap-2.5">
          <span
            aria-hidden="true"
            className="grid size-9 place-items-center rounded-[10px] bg-[var(--brand)] text-sm font-bold text-white"
          >
            SB
          </span>
          <span className="text-lg font-semibold tracking-tight">Sehat Bridge</span>
        </div>
        <span className="rounded-full bg-[var(--brand-weak)] px-3 py-1 text-xs font-medium text-[var(--brand-ink)]">
          M0 · Fondasi
        </span>
      </header>

      <section className="flex flex-1 flex-col justify-center py-20">
        <p className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--brand)]">
          Platform faskes Indonesia
        </p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
          Satu alur untuk berkas, anggota, dan integrasi{" "}
          <span className="italic text-[var(--brand)]">faskes</span>.
        </h1>
        <p className="mt-6 max-w-xl text-lg text-[var(--ink-2)]">
          Fondasi multi-tenant dengan isolasi data per fasilitas, autentikasi yang aman, dan
          integrasi SATUSEHAT yang bisa diuji tanpa akses produksi.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-3">
          <a
            href="/api/docs"
            className="rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-ink)]"
          >
            Lihat API
          </a>
          <a
            href="https://github.com/Harisalghifary/sehat-bridge"
            className="rounded-md border border-[var(--line)] px-5 py-3 text-sm font-semibold text-[var(--ink)] transition-colors hover:bg-[var(--bg-alt)]"
          >
            Repositori
          </a>
        </div>

        <div className="mt-12 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[10px] border border-[var(--line)] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">API</p>
            <p
              className={`mt-1 flex items-center gap-2 text-sm font-semibold ${
                healthy ? "text-[var(--ok)]" : "text-[var(--danger)]"
              }`}
            >
              <span
                aria-hidden="true"
                className={`size-2 rounded-full ${healthy ? "bg-[var(--ok)]" : "bg-[var(--danger)]"}`}
              />
              {healthy ? `siap · v${health.version}` : health.status}
            </p>
          </div>
          <div className="rounded-[10px] border border-[var(--line)] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              Basis data
            </p>
            <p className="mt-1 text-sm font-semibold">schema per tenant</p>
          </div>
          <div className="rounded-[10px] border border-[var(--line)] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--muted)]">
              SATUSEHAT
            </p>
            <p className="mt-1 text-sm font-semibold">mode uji</p>
          </div>
        </div>
      </section>

      <footer className="flex flex-col gap-2 border-t border-[var(--line)] pt-6 text-sm text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between">
        <p>
          Sehat Bridge adalah proyek independen dan tidak berafiliasi dengan Kemenkes.
        </p>
        <p>v0.1.0 · fondasi</p>
      </footer>
    </main>
  );
}