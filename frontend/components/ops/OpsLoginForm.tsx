"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const inputClass =
  "mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2 text-sm focus:border-[var(--brand)] focus:outline-none";

export function OpsLoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setError(null);

    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    const nextErrors: typeof fieldErrors = {};
    if (!email) nextErrors.email = "Email wajib diisi.";
    if (!password) nextErrors.password = "Kata sandi wajib diisi.";
    setFieldErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    setPending(true);
    try {
      const response = await fetch("/api/ops/session", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        if (response.status === 401) {
          setError("Email atau kata sandi salah, atau akun bukan operator platform.");
        } else if (response.status === 429) {
          setError("Terlalu banyak percobaan. Tunggu beberapa menit lalu coba lagi.");
        } else {
          setError("Tidak dapat masuk ke konsol operator.");
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
        <label htmlFor="ops-email" className="text-sm font-medium">
          Email operator
        </label>
        <input
          id="ops-email"
          name="email"
          type="email"
          required
          autoComplete="username"
          className={inputClass}
          aria-invalid={Boolean(fieldErrors.email)}
          onChange={() => setFieldErrors((value) => ({ ...value, email: undefined }))}
        />
        {fieldErrors.email ? (
          <p className="mt-1 text-xs text-[var(--danger)]">{fieldErrors.email}</p>
        ) : null}
      </div>
      <div>
        <label htmlFor="ops-password" className="text-sm font-medium">
          Kata sandi
        </label>
        <input
          id="ops-password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          className={inputClass}
          aria-invalid={Boolean(fieldErrors.password)}
          onChange={() =>
            setFieldErrors((value) => ({ ...value, password: undefined }))
          }
        />
        {fieldErrors.password ? (
          <p className="mt-1 text-xs text-[var(--danger)]">{fieldErrors.password}</p>
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
        {pending ? "Memeriksa…" : "Masuk ke konsol"}
      </button>
    </form>
  );
}