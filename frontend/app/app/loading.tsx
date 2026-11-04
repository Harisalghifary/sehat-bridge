export default function AppLoading() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <span className="sr-only">Memuat halaman…</span>
      <div className="h-8 w-56 animate-pulse rounded bg-[var(--line)]" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((item) => (
          <div
            key={item}
            className="h-28 animate-pulse rounded-[10px] border border-[var(--line)] bg-white"
          />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-[10px] border border-[var(--line)] bg-white" />
    </div>
  );
}