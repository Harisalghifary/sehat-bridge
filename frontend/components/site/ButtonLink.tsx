import Link from "next/link";
import type { ComponentProps } from "react";

type Variant = "primary" | "secondary" | "quiet";

const styles: Record<Variant, string> = {
  primary:
    "bg-[var(--brand)] text-white hover:bg-[var(--brand-ink)] border border-transparent",
  secondary:
    "border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--bg-alt)]",
  quiet:
    "border border-transparent text-[var(--ink-2)] hover:text-[var(--ink)]",
};

export function ButtonLink({
  href,
  variant = "primary",
  className = "",
  children,
  ...rest
}: {
  href: string;
  variant?: Variant;
  className?: string;
  children: React.ReactNode;
} & Omit<ComponentProps<typeof Link>, "href" | "className" | "children">) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 py-3 text-sm font-semibold transition-colors ${styles[variant]} ${className}`}
      {...rest}
    >
      {children}
    </Link>
  );
}