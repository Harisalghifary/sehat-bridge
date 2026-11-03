import Link from "next/link";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`group inline-flex items-center gap-2.5 rounded-md ${className}`}
    >
      <span
        aria-hidden="true"
        className="grid size-9 place-items-center rounded-[10px] bg-[var(--brand)] text-sm font-bold text-white transition-colors group-hover:bg-[var(--brand-ink)]"
      >
        SB
      </span>
      <span className="text-[17px] font-semibold tracking-tight">
        Sehat Bridge
      </span>
    </Link>
  );
}