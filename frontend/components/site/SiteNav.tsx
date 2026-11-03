"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Logo } from "@/components/site/Logo";
import { navItems } from "@/lib/site";

const FOCUSABLE =
  'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function SiteNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (nodes.length === 0) return;
      const firstNode = nodes[0];
      const lastNode = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === firstNode) {
        event.preventDefault();
        lastNode.focus();
      } else if (!event.shiftKey && document.activeElement === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  function close() {
    setOpen(false);
    toggleRef.current?.focus();
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-white">
      <div className="container-site flex h-[72px] items-center justify-between gap-6">
        <Logo />

        <nav aria-label="Navigasi utama" className="hidden lg:block">
          <ul className="flex items-center gap-7">
            {navItems.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={pathname === item.href ? "page" : undefined}
                  className={`rounded-md text-sm font-medium transition-colors hover:text-[var(--brand)] ${
                    pathname === item.href
                      ? "text-[var(--brand)]"
                      : "text-[var(--ink-2)]"
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Link
            href="/masuk"
            className="rounded-md px-2 py-2 text-sm font-semibold text-[var(--ink-2)] hover:text-[var(--ink)]"
          >
            Masuk
          </Link>
          <Link
            href="/demo"
            className="inline-flex min-h-10 items-center rounded-md bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-ink)]"
          >
            Jadwalkan demo
          </Link>
        </div>

        <button
          ref={toggleRef}
          type="button"
          className="inline-flex size-11 items-center justify-center rounded-md border border-[var(--line)] text-[var(--ink)] lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Tutup menu" : "Buka menu"}
          onClick={() => setOpen((value) => !value)}
        >
          <span aria-hidden="true" className="relative block h-4 w-5">
            <span
              className={`absolute left-0 top-0 h-0.5 w-5 bg-current transition-transform ${
                open ? "translate-y-[7px] rotate-45" : ""
              }`}
            />
            <span
              className={`absolute left-0 top-[7px] h-0.5 w-5 bg-current transition-opacity ${
                open ? "opacity-0" : ""
              }`}
            />
            <span
              className={`absolute left-0 top-[14px] h-0.5 w-5 bg-current transition-transform ${
                open ? "-translate-y-[7px] -rotate-45" : ""
              }`}
            />
          </span>
        </button>
      </div>

      {open ? (
        <div
          ref={panelRef}
          id="mobile-nav"
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
          className="fixed inset-x-0 top-[72px] bottom-0 z-50 overflow-y-auto border-t border-[var(--line)] bg-white lg:hidden"
        >
          <div className="container-site py-6">
            <button
              type="button"
              onClick={close}
              className="ml-auto flex min-h-11 items-center rounded-md border border-[var(--line)] px-4 text-sm font-semibold"
            >
              Tutup
            </button>
            <nav aria-label="Navigasi seluler" className="mt-4">
              <ul className="divide-y divide-[var(--line)]">
                {navItems.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={close}
                      className="flex min-h-14 items-center text-lg font-medium"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
                <li>
                  <Link
                    href="/masuk"
                    onClick={close}
                    className="flex min-h-14 items-center text-lg font-medium"
                  >
                    Masuk
                  </Link>
                </li>
              </ul>
            </nav>
            <Link
              href="/demo"
              onClick={close}
              className="mt-6 flex min-h-12 items-center justify-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white"
            >
              Jadwalkan demo
            </Link>
          </div>
        </div>
      ) : null}
    </header>
  );
}