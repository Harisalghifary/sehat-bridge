type Variant = "dashboard" | "files" | "members" | "integration" | "audit";

const variantLabel: Record<Variant, string> = {
  dashboard: "Dasbor faskes",
  files: "Daftar berkas",
  members: "Anggota dan peran",
  integration: "Integrasi SATUSEHAT",
  audit: "Jejak audit",
};

export function AppPreview({
  variant = "dashboard",
  caption = "Ilustrasi antarmuka dengan data contoh. Tampilan sebenarnya dibangun pada tahap berikutnya.",
}: {
  variant?: Variant;
  caption?: string;
}) {
  return (
    <figure className="m-0">
      <div
        aria-hidden="true"
        className="overflow-hidden rounded-[12px] border border-[var(--line)] bg-white shadow-[0_1px_2px_rgba(11,31,42,0.06)]"
      >
        <div className="flex items-center gap-2 border-b border-[var(--line)] bg-[var(--bg-alt)] px-4 py-2.5">
          <span className="size-2 rounded-full bg-[#d9e2e7]" />
          <span className="size-2 rounded-full bg-[#d9e2e7]" />
          <span className="size-2 rounded-full bg-[#d9e2e7]" />
          <span className="ml-3 truncate rounded-md border border-[var(--line)] bg-white px-3 py-1 text-[11px] text-[var(--muted)]">
            app.sehatbridge.local/{variant === "dashboard" ? "dasbor" : variant}
          </span>
        </div>
        <div className="grid min-h-[300px] grid-cols-[132px_1fr] sm:grid-cols-[164px_1fr]">
          <div className="border-r border-[var(--line)] bg-white p-3">
            <div className="flex items-center gap-2">
              <span className="grid size-6 place-items-center rounded-md bg-[var(--brand)] text-[9px] font-bold text-white">
                SB
              </span>
              <span className="text-[10px] font-semibold">Klinik Sehat</span>
            </div>
            <div className="mt-5 space-y-1">
              {["Dasbor", "Berkas", "Anggota", "Integrasi", "Profil"].map(
                (item, index) => (
                  <div
                    key={item}
                    className={`rounded px-2 py-1.5 text-[10px] ${
                      index === 0
                        ? "bg-[var(--brand-weak)] font-semibold text-[var(--brand-ink)]"
                        : "text-[var(--ink-2)]"
                    }`}
                  >
                    {item}
                  </div>
                ),
              )}
            </div>
          </div>
          <div className="bg-[var(--bg-alt)] p-3 sm:p-4">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold">{variantLabel[variant]}</p>
              <span className="rounded-full bg-white px-2 py-0.5 text-[9px] text-[var(--muted)] ring-1 ring-[var(--line)]">
                Mode uji
              </span>
            </div>
            <div className="mt-3">{body(variant)}</div>
          </div>
        </div>
      </div>
      <figcaption className="mt-3 text-xs leading-5 text-[var(--muted)]">
        {caption}
      </figcaption>
    </figure>
  );
}

function body(variant: Variant) {
  if (variant === "files") return <FilesBody />;
  if (variant === "members") return <MembersBody />;
  if (variant === "integration") return <IntegrationBody />;
  if (variant === "audit") return <AuditBody />;
  return <DashboardBody />;
}

function DashboardBody() {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {[
          ["Berkas", "24"],
          ["Kuota", "38%"],
          ["Sinkronisasi", "Selesai"],
          ["Integrasi", "Mode uji"],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-[var(--line)] bg-white p-3"
          >
            <p className="text-[9px] uppercase tracking-wide text-[var(--muted)]">
              {label}
            </p>
            <p className="mt-1 text-sm font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-[var(--line)] bg-white p-3">
        <div className="flex items-center justify-between text-[10px]">
          <span className="font-semibold">Kuota penyimpanan</span>
          <span className="text-[var(--muted)]">0,38 dari 1 GB</span>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-[var(--line)]">
          <div className="h-1.5 w-[38%] rounded-full bg-[var(--brand)]" />
        </div>
      </div>
      <div className="space-y-2 rounded-md border border-[var(--line)] bg-white p-3">
        {["Berkas diunggah", "Integrasi diuji", "Peran diperbarui"].map(
          (item) => (
            <div
              key={item}
              className="flex items-center justify-between border-b border-[var(--line)] pb-2 text-[10px] last:border-0 last:pb-0"
            >
              <span>{item}</span>
              <span className="text-[var(--muted)]">baru saja</span>
            </div>
          ),
        )}
      </div>
    </div>
  );
}

function FilesBody() {
  return (
    <div className="rounded-md border border-[var(--line)] bg-white">
      <div className="flex items-center justify-between border-b border-[var(--line)] p-3">
        <div>
          <p className="text-[10px] font-semibold">Berkas faskes</p>
          <p className="text-[9px] text-[var(--muted)]">PDF, CSV, PNG · maks 25 MB</p>
        </div>
        <span className="rounded bg-[var(--brand)] px-2 py-1 text-[9px] font-semibold text-white">
          Unggah
        </span>
      </div>
      {[
        ["hasil-lab.pdf", "Siap", "admin"],
        ["stok-obat.csv", "Siap", "owner"],
        ["ruang-tunggu.png", "Siap", "admin"],
      ].map(([name, status, role]) => (
        <div
          key={name}
          className="grid grid-cols-[1fr_auto_auto] items-center gap-3 border-b border-[var(--line)] px-3 py-2.5 text-[10px] last:border-0"
        >
          <span className="truncate font-medium">{name}</span>
          <span className="rounded-full bg-[var(--brand-weak)] px-2 py-0.5 text-[9px] text-[var(--brand-ink)]">
            {status}
          </span>
          <span className="text-[var(--muted)]">{role}</span>
        </div>
      ))}
    </div>
  );
}

function MembersBody() {
  return (
    <div className="rounded-md border border-[var(--line)] bg-white">
      <div className="flex items-center justify-between border-b border-[var(--line)] p-3">
        <p className="text-[10px] font-semibold">Anggota tenant</p>
        <span className="rounded border border-[var(--line)] px-2 py-1 text-[9px] text-[var(--muted)]">
          Undang segera hadir
        </span>
      </div>
      {[
        ["owner@klinik.example", "Owner"],
        ["admin@klinik.example", "Admin"],
        ["staf@klinik.example", "Member"],
      ].map(([email, role]) => (
        <div
          key={email}
          className="flex items-center justify-between border-b border-[var(--line)] px-3 py-2.5 text-[10px] last:border-0"
        >
          <span className="truncate">{email}</span>
          <span className="rounded bg-[var(--bg-alt)] px-2 py-0.5 text-[9px] font-medium">
            {role}
          </span>
        </div>
      ))}
      <p className="px-3 py-2 text-[9px] text-[var(--muted)]">
        Owner terakhir tidak dapat diturunkan perannya.
      </p>
    </div>
  );
}

function IntegrationBody() {
  return (
    <div className="space-y-3">
      <div className="rounded-md border border-[var(--line)] bg-white p-3">
        <div className="flex items-center justify-between text-[10px]">
          <span className="font-semibold">SATUSEHAT</span>
          <span className="rounded-full bg-[#fff6e5] px-2 py-0.5 text-[9px] text-[var(--warn)]">
            Mode uji
          </span>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2 text-[9px] text-[var(--muted)]">
          <span>Status: terhubung</span>
          <span>Organisasi: terpetakan</span>
        </div>
      </div>
      <div className="rounded-md border border-[var(--line)] bg-white">
        {[
          ["organization", "done"],
          ["patient", "queued"],
        ].map(([kind, status]) => (
          <div
            key={kind}
            className="flex items-center justify-between border-b border-[var(--line)] px-3 py-2.5 text-[10px] last:border-0"
          >
            <span>{kind}</span>
            <span
              className={
                status === "done"
                  ? "text-[var(--ok)]"
                  : "text-[var(--warn)]"
              }
            >
              {status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AuditBody() {
  return (
    <div className="rounded-md border border-[var(--line)] bg-white p-3">
      {[
        ["user.role_changed", "admin → member"],
        ["file.completed", "hasil-lab.pdf"],
        ["integration.sync_done", "organization"],
        ["auth.login", "owner@klinik.example"],
      ].map(([action, detail]) => (
        <div
          key={action}
          className="flex items-center justify-between gap-3 border-b border-[var(--line)] py-2 text-[10px] last:border-0"
        >
          <span className="font-mono text-[9px] text-[var(--brand-ink)]">
            {action}
          </span>
          <span className="truncate text-right text-[var(--muted)]">
            {detail}
          </span>
        </div>
      ))}
    </div>
  );
}