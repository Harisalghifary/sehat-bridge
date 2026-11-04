"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { NavIcon } from "@/components/app/NavIcon";

const NAV = [
  { href: "/ops/tenant", label: "Tenant", icon: "tenants" },
  { href: "/ops/audit", label: "Audit", icon: "audit" },
  { href: "/ops/kesehatan", label: "Kesehatan", icon: "health" },
];

export function OpsShell({
  email,
  children,
}: {
  email: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function signOut() {
    setPending(true);
    try {
      await fetch("/api/ops/session", { method: "DELETE" });
    } finally {
      router.replace("/ops/masuk");
      router.refresh();
    }
  }

  return (
    <div className="min-h-dvh bg-[var(--bg-alt)]">
      <a href="#ops-main" className="skip-link">
        Lewati ke konten
      </a>
      <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-[var(--ink)] text-white">
        <div className="mx-auto flex min-h-[60px] max-w-[1320px] flex-wrap items-center justify-between gap-2 px-4 py-2 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/ops/tenant" className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                className="grid size-8 place-items-center rounded-lg bg-white text-[11px] font-bold text-[var(--ink)]"
              >
                SB
              </span>
              <span className="text-sm font-semibold tracking-tight">
                Sehat Bridge
              </span>
            </Link>
            <span className="rounded-full border border-white/25 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide">
              Operator platform
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden max-w-[220px] truncate text-xs text-white/70 sm:inline">
              {email}
            </span>
            <Link
              href="/"
              className="hidden min-h-11 items-center px-2 text-xs text-white/80 hover:text-white sm:inline-flex"
            >
              Situs publik
            </Link>
            <button
              type="button"
              onClick={() => void signOut()}
              disabled={pending}
              className="min-h-11 rounded-md border border-white/30 px-3 text-xs font-semibold text-white hover:bg-white/10 disabled:opacity-60"
            >
              {pending ? "Keluar…" : "Keluar"}
            </button>
          </div>
        </div>
        <nav aria-label="Navigasi operator" className="mx-auto max-w-[1320px] px-4 sm:px-6">
          <ul className="flex gap-1 overflow-x-auto">
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex min-h-11 items-center gap-2 border-b-2 px-3 text-sm font-medium ${
                      active
                        ? "border-white text-white"
                        : "border-transparent text-white/65 hover:text-white"
                    }`}
                  >
                    <NavIcon name={item.icon} />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </header>
      <main id="ops-main" className="mx-auto max-w-[1320px] px-4 py-6 sm:px-6 sm:py-8">
        {children}
      </main>
    </div>
  );
}