"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { NavIcon } from "@/components/app/NavIcon";
import { breadcrumbLabels } from "@/lib/app-nav";
import { initials, roleLabel } from "@/lib/format";

type NavItem = {
  href: string;
  label: string;
  icon: string;
};

type Props = {
  isPlatformAdmin?: boolean;
  user: {
    name: string;
    email: string;
    role: string;
    tenantName: string;
    tenantSlug: string;
  };
  nav: NavItem[];
  children: React.ReactNode;
};

const FOCUSABLE =
  'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function AppShell({ user, nav, isPlatformAdmin, children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    panel?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (!nodes.length) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previous;
    };
  }, [open]);

  async function signOut(allSessions = false) {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await fetch("/api/session", {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ all_sessions: allSessions }),
      });
    } finally {
      router.replace("/masuk");
      router.refresh();
    }
  }

  const segments = pathname.split("/").filter(Boolean);
  const crumbs = segments.map((segment, index) => ({
    label: breadcrumbLabels[segment] ?? segment,
    href: `/${segments.slice(0, index + 1).join("/")}`,
  }));

  return (
    <div className="min-h-dvh bg-[var(--bg-alt)]">
      <a href="#app-main" className="skip-link">
        Lewati ke konten
      </a>

      <header className="sticky top-0 z-40 border-b border-[var(--line)] bg-white">
        <div className="mx-auto flex h-[64px] max-w-[1320px] items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              ref={toggleRef}
              type="button"
              onClick={() => setOpen(true)}
              aria-expanded={open}
              aria-controls="app-drawer"
              aria-label="Buka navigasi"
              className="inline-flex size-11 items-center justify-center rounded-md border border-[var(--line)] lg:hidden"
            >
              <span aria-hidden="true" className="space-y-1">
                <span className="block h-0.5 w-5 bg-current" />
                <span className="block h-0.5 w-5 bg-current" />
                <span className="block h-0.5 w-5 bg-current" />
              </span>
            </button>
            <Link href="/app/dasbor" className="flex items-center gap-2.5">
              <span
                aria-hidden="true"
                className="grid size-8 place-items-center rounded-lg bg-[var(--brand)] text-[11px] font-bold text-white"
              >
                SB
              </span>
              <span className="text-sm font-semibold tracking-tight">
                Sehat Bridge
              </span>
            </Link>
            <span className="hidden rounded-full border border-[var(--line)] bg-[var(--bg-alt)] px-2.5 py-1 text-xs font-medium text-[var(--ink-2)] sm:inline">
              {user.tenantName}
            </span>
          </div>

          <details className="group relative">
            <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 rounded-md px-2 text-sm hover:bg-[var(--bg-alt)] [&::-webkit-details-marker]:hidden">
              <span className="grid size-8 place-items-center rounded-full bg-[var(--brand-weak)] text-xs font-semibold text-[var(--brand-ink)]">
                {initials(user.name, user.email)}
              </span>
              <span className="hidden text-left sm:block">
                <span className="block max-w-[160px] truncate text-sm font-medium">
                  {user.name}
                </span>
                <span className="block text-[11px] text-[var(--muted)]">
                  {roleLabel(user.role)}
                </span>
              </span>
            </summary>
            <div className="absolute right-0 top-full z-50 mt-2 w-56 rounded-md border border-[var(--line)] bg-white p-1 shadow-[0_1px_2px_rgba(11,31,42,0.06)]">
              <div className="border-b border-[var(--line)] px-3 py-2">
                <p className="truncate text-sm font-medium">{user.email}</p>
                <p className="mt-0.5 text-xs text-[var(--muted)]">
                  {user.tenantSlug} · {roleLabel(user.role)}
                </p>
              </div>
              {isPlatformAdmin ? (
                <Link
                  href="/ops/tenant"
                  className="block rounded px-3 py-2 text-sm font-medium text-[var(--brand-ink)] hover:bg-[var(--brand-weak)]"
                >
                  Konsol operator
                </Link>
              ) : null}
              <Link
                href="/app/profil"
                className="block rounded px-3 py-2 text-sm hover:bg-[var(--bg-alt)]"
              >
                Profil
              </Link>
              <Link
                href="/app/pengaturan"
                className="block rounded px-3 py-2 text-sm hover:bg-[var(--bg-alt)]"
              >
                Pengaturan
              </Link>
              <button
                type="button"
                onClick={() => signOut(false)}
                disabled={signingOut}
                className="block w-full rounded px-3 py-2 text-left text-sm text-[var(--danger)] hover:bg-[#fdf0f0] disabled:opacity-60"
              >
                Keluar
              </button>
            </div>
          </details>
        </div>
      </header>

      <div className="mx-auto flex max-w-[1320px]">
        <aside className="hidden w-[240px] shrink-0 border-r border-[var(--line)] bg-white lg:block">
          <div className="sticky top-[64px] flex h-[calc(100dvh-64px)] flex-col p-4">
            <SidebarNav nav={nav} pathname={pathname} />
            <div className="mt-auto space-y-2 border-t border-[var(--line)] pt-4 text-xs text-[var(--muted)]">
              <p className="rounded-md bg-[#fff6e5] px-2.5 py-2 text-[var(--warn)]">
                Mode uji · integrasi belum produksi
              </p>
              <p>v0.1.0 · {user.tenantSlug}</p>
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <div className="border-b border-[var(--line)] bg-white px-4 py-2.5 sm:px-6">
            <nav aria-label="Breadcrumb">
              <ol className="flex flex-wrap items-center gap-1.5 text-xs text-[var(--muted)]">
                {crumbs.map((crumb, index) => (
                  <li key={crumb.href} className="flex items-center gap-1.5">
                    {index > 0 ? <span aria-hidden="true">/</span> : null}
                    {index === crumbs.length - 1 ? (
                      <span aria-current="page" className="text-[var(--ink-2)]">
                        {crumb.label}
                      </span>
                    ) : (
                      <Link href={crumb.href} className="hover:text-[var(--ink)]">
                        {crumb.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          </div>
          <main id="app-main" className="px-4 py-6 sm:px-6 sm:py-8">
            {children}
          </main>
        </div>
      </div>

      {open ? (
        <div
          ref={panelRef}
          id="app-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Navigasi aplikasi"
          className="fixed inset-0 z-50 bg-[var(--ink)]/30 lg:hidden"
        >
          <div className="h-full w-[280px] max-w-[85vw] overflow-y-auto bg-white p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Menu</span>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  toggleRef.current?.focus();
                }}
                className="min-h-11 rounded-md border border-[var(--line)] px-3 text-sm font-medium"
              >
                Tutup
              </button>
            </div>
            <div className="mt-5">
              <SidebarNav
                nav={nav}
                pathname={pathname}
                onNavigate={() => setOpen(false)}
              />
            </div>
            <button
              type="button"
              onClick={() => signOut(false)}
              disabled={signingOut}
              className="mt-8 min-h-11 w-full rounded-md border border-[#f0c9cb] px-4 text-sm font-semibold text-[var(--danger)]"
            >
              Keluar
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SidebarNav({
  nav,
  pathname,
  onNavigate,
}: {
  nav: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav aria-label="Navigasi aplikasi">
      <ul className="space-y-1">
        {nav.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium ${
                  active
                    ? "bg-[var(--brand-weak)] text-[var(--brand-ink)]"
                    : "text-[var(--ink-2)] hover:bg-[var(--bg-alt)] hover:text-[var(--ink)]"
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
  );
}