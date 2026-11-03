"use client";

import { useRouter } from "next/navigation";

const items = [
  { id: "berkas", label: "Berkas" },
  { id: "anggota", label: "Anggota & peran" },
  { id: "integrasi", label: "Integrasi" },
  { id: "audit", label: "Audit" },
];

export function SolutionNav() {
  const router = useRouter();

  return (
    <div className="sticky top-[72px] z-30 border-b border-[var(--line)] bg-white/95">
      <div className="container-site flex items-center gap-6 py-3">
        <nav aria-label="Kategori solusi" className="hidden md:block">
          <ul className="flex flex-wrap gap-2">
            {items.map((item) => (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className="inline-flex min-h-9 items-center rounded-full border border-[var(--line)] px-3 text-xs font-medium text-[var(--ink-2)] hover:border-[var(--brand)] hover:text-[var(--brand)]"
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <label className="flex w-full items-center gap-3 text-sm md:hidden">
          <span className="shrink-0 font-medium">Kategori</span>
          <select
            className="min-h-10 w-full rounded-md border border-[var(--line)] bg-white px-3 text-sm"
            defaultValue=""
            onChange={(event) => {
              const id = event.target.value;
              if (!id) return;
              document.getElementById(id)?.scrollIntoView();
              router.replace(`#${id}`, { scroll: false });
            }}
          >
            <option value="" disabled>
              Pilih bagian
            </option>
            {items.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}