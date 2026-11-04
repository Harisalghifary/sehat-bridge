"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const inputClass =
  "mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2 text-sm focus:border-[var(--brand)] focus:outline-none";

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{
    tenant_slug?: string;
    email?: string;
    password?: string;
  }>({});

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setError(null);

    const data = new FormData(event.currentTarget);
    const tenantSlug = String(data.get("tenant_slug") ?? "").trim();
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    const nextErrors: typeof fieldErrors = {};
    if (!tenantSlug) nextErrors.tenant_slug = "Kode faskes wajib diisi.";
    if (!email) nextErrors.email = "Email wajib diisi.";
    if (!email.includes("@")) nextErrors.email = "Format email belum benar.";
    if (!password) nextErrors.password = "Kata sandi wajib diisi.";
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setPending(true);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          tenant_slug: tenantSlug,
          email,
          password,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError("Email atau kata sandi salah.");
        } else if (response.status === 429) {
          setError("Terlalu banyak percobaan. Tunggu beberapa menit lalu coba lagi.");
        } else if (response.status === 403) {
          setError("Akun ini tidak terhubung ke faskes yang aktif.");
        } else if (response.status === 503) {
          setError("Layanan sedang tidak tersedia. Coba lagi sesaat.");
        } else {
          setError("Tidak dapat masuk. Periksa kembali isian Anda.");
        }
        return;
      }

      router.replace(next);
      router.refresh();
    } catch {
      setError("Koneksi terputus. Periksa jaringan lalu coba lagi.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="tenant_slug" className="text-sm font-medium">
          Kode faskes
        </label>
        <input
          id="tenant_slug"
          name="tenant_slug"
          required
          autoComplete="organization"
          autoCapitalize="none"
          spellCheck={false}
          className={inputClass}
          placeholder="acme"
          aria-invalid={Boolean(fieldErrors.tenant_slug)}
          aria-describedby="tenant_slug_help"
          onChange={() =>
            setFieldErrors((value) => ({ ...value, tenant_slug: undefined }))
          }
        />
        {fieldErrors.tenant_slug ? (
          <p id="tenant_slug_help" className="mt-1 text-xs text-[var(--danger)]">
            {fieldErrors.tenant_slug}
          </p>
        ) : null}
        <p className="mt-1 text-xs text-[var(--muted)]">
          Kode diberikan oleh admin faskes Anda.
        </p>
      </div>

      <div>
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="username"
          className={inputClass}
          placeholder="nama@klinik.example"
          aria-invalid={Boolean(fieldErrors.email)}
          aria-describedby={fieldErrors.email ? "email_error" : undefined}
          onChange={() =>
            setFieldErrors((value) => ({ ...value, email: undefined }))
          }
        />
        {fieldErrors.email ? (
          <p id="email_error" className="mt-1 text-xs text-[var(--danger)]">
            {fieldErrors.email}
          </p>
        ) : null}
      </div>

      <div>
        <label htmlFor="password" className="text-sm font-medium">
          Kata sandi
        </label>
        <div className="relative">
          <input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            required
            autoComplete="current-password"
            className={`${inputClass} pr-20`}
            aria-invalid={Boolean(fieldErrors.password)}
            aria-describedby={fieldErrors.password ? "password_error" : undefined}
            onChange={() =>
              setFieldErrors((value) => ({ ...value, password: undefined }))
            }
          />
          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            className="absolute inset-y-0 right-0 mt-1.5 inline-flex min-h-11 items-center rounded-r-md px-3 text-xs font-semibold text-[var(--ink-2)] hover:text-[var(--ink)]"
            aria-pressed={showPassword}
          >
            {showPassword ? "Sembunyikan" : "Lihat"}
          </button>
        </div>
        {fieldErrors.password ? (
          <p id="password_error" className="mt-1 text-xs text-[var(--danger)]">
            {fieldErrors.password}
          </p>
        ) : null}
      </div>

      {error ? (
        <p
          role="alert"
          className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-3 py-2 text-sm text-[var(--danger)]"
        >
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--brand-ink)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Memeriksa…" : "Masuk"}
      </button>
    </form>
  );
}