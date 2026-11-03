import Link from "next/link";

import { Logo } from "@/components/site/Logo";
import { footerColumns, site, whatsappHref } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-[var(--line)] bg-white">
      <div className="container-site py-14 sm:py-16">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-sm leading-6 text-[var(--ink-2)]">
              Platform untuk klinik, laboratorium, dan praktik mandiri yang
              ingin merapikan berkas dan alur integrasi tanpa menunggu akses
              produksi.
            </p>
            <div className="mt-5 space-y-1 text-sm text-[var(--ink-2)]">
              <p>{site.location}</p>
              <p>
                <a className="underline underline-offset-4" href={`mailto:${site.email}`}>
                  {site.email}
                </a>
              </p>
              <p>
                <a
                  className="underline underline-offset-4"
                  href={whatsappHref}
                  rel="noreferrer"
                  target="_blank"
                >
                  WhatsApp {site.whatsappDisplay}
                </a>
              </p>
            </div>
          </div>

          {footerColumns.map((column) => (
            <div key={column.title}>
              <h2 className="text-sm font-semibold">{column.title}</h2>
              <ul className="mt-4 space-y-3 text-sm">
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[var(--ink-2)] hover:text-[var(--ink)]"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col gap-4 border-t border-[var(--line)] pt-6 text-xs text-[var(--muted)] sm:flex-row sm:items-start sm:justify-between">
          <p className="max-w-2xl">
            {site.disclaimer} Nama SATUSEHAT merujuk pada program resmi
            Kemenkes; Sehat Bridge hanya menyediakan adapter dan tidak mengklaim
            afiliasi.
          </p>
          <p>© 2026 Sehat Bridge · v0.1.0</p>
        </div>
      </div>
    </footer>
  );
}