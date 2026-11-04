const tones: Record<string, string> = {
  ready: "bg-[var(--brand-weak)] text-[var(--brand-ink)] border-[#cbe6e2]",
  done: "bg-[var(--brand-weak)] text-[var(--brand-ink)] border-[#cbe6e2]",
  connected: "bg-[var(--brand-weak)] text-[var(--brand-ink)] border-[#cbe6e2]",
  uploading: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
  queued: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
  running: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
  unverified: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
  deleted: "bg-[var(--bg-alt)] text-[var(--ink-2)] border-[var(--line)]",
  failed: "bg-[#fdf0f0] text-[var(--danger)] border-[#f0c9cb]",
  dead: "bg-[#fdf0f0] text-[var(--danger)] border-[#f0c9cb]",
  error: "bg-[#fdf0f0] text-[var(--danger)] border-[#f0c9cb]",
};

const labels: Record<string, string> = {
  uploading: "Mengunggah",
  ready: "Siap",
  deleted: "Dihapus",
  queued: "Antre",
  running: "Berjalan",
  done: "Selesai",
  failed: "Gagal",
  dead: "Berhenti",
  unverified: "Belum diuji",
  connected: "Terhubung",
  error: "Error",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${
        tones[status] ?? "bg-[var(--bg-alt)] text-[var(--ink-2)] border-[var(--line)]"
      }`}
    >
      <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
      {labels[status] ?? status}
    </span>
  );
}