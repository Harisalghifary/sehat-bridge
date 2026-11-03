type Tone = "test" | "planned" | "ready";

const tones: Record<Tone, { chip: string; dot: string }> = {
  test: {
    chip: "bg-[#fff6e5] text-[var(--warn)] border-[#f0dfbc]",
    dot: "bg-[var(--warn)]",
  },
  planned: {
    chip: "bg-[var(--bg-alt)] text-[var(--ink-2)] border-[var(--line)]",
    dot: "bg-[var(--muted)]",
  },
  ready: {
    chip: "bg-[var(--brand-weak)] text-[var(--brand-ink)] border-[#cbe6e2]",
    dot: "bg-[var(--ok)]",
  },
};

export function StatusChip({
  tone,
  children,
}: {
  tone: Tone;
  children: React.ReactNode;
}) {
  const style = tones[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${style.chip}`}
    >
      <span aria-hidden="true" className={`size-1.5 rounded-full ${style.dot}`} />
      {children}
    </span>
  );
}