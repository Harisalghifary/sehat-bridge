"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const inputClass =
  "mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2 text-sm focus:border-[var(--brand)] focus:outline-none";

function SubmitButton({ pending, label }: { pending: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex min-h-11 w-full items-center justify-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white hover:bg-[var(--brand-ink)] disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending ? "Memproses…" : label}
    </button>
  );
}

export function PasswordResetRequestForm() {
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setError(null);
    const email = String(new FormData(event.currentTarget).get("email") ?? "").trim();
    if (!email.includes("@")) {
      setError("Masukkan alamat email yang valid.");
      return;
    }
    setPending(true);
    try {
      const response = await fetch("/api/auth/password-reset/request", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (response.status === 429) {
        setError("Terlalu banyak permintaan. Tunggu beberapa menit lalu coba lagi.");
        return;
      }
      if (!response.ok) {
        setError("Permintaan tidak dapat diproses. Coba lagi sesaat.");
        return;
      }
      setSent(true);
    } catch {
      setError("Koneksi terputus. Periksa jaringan lalu coba lagi.");
    } finally {
      setPending(false);
    }
  }

  if (sent) {
    return (
      <div role="status" className="space-y-4">
        <p className="rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] px-4 py-3 text-sm text-[var(--brand-ink)]">
          Jika alamat itu terdaftar, tautan pengaturan ulang sudah dikirim.
          Periksa kotak masuk dan folder spam.
        </p>
        <Link
          href="/masuk"
          className="inline-flex min-h-11 items-center justify-center rounded-md border border-[var(--line)] px-5 text-sm font-semibold"
        >
          Kembali ke halaman masuk
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="reset-email" className="text-sm font-medium">
          Email akun
        </label>
        <input
          id="reset-email"
          name="email"
          type="email"
          required
          autoComplete="username"
          className={inputClass}
          placeholder="nama@klinik.example"
        />
      </div>
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-3 py-2 text-sm text-[var(--danger)]"
        >
          {error}
        </p>
      ) : null}
      <SubmitButton pending={pending} label="Kirim tautan reset" />
    </form>
  );
}

export function PasswordResetConfirmForm({ token }: { token: string }) {
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setError(null);
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password") ?? "");
    const confirmation = String(data.get("confirmation") ?? "");
    if (password.length < 12) {
      setError("Kata sandi minimal 12 karakter.");
      return;
    }
    if (password !== confirmation) {
      setError("Konfirmasi kata sandi belum sama.");
      return;
    }
    setPending(true);
    try {
      const response = await fetch("/api/auth/password-reset/confirm", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as {
          title?: string;
        };
        setError(problem.title || "Tautan tidak valid atau sudah kedaluwarsa.");
        return;
      }
      setDone(true);
    } catch {
      setError("Koneksi terputus. Periksa jaringan lalu coba lagi.");
    } finally {
      setPending(false);
    }
  }

  if (!token) {
    return (
      <p role="alert" className="text-sm text-[var(--danger)]">
        Tautan tidak lengkap. Minta tautan baru dari halaman lupa kata sandi.
      </p>
    );
  }

  if (done) {
    return (
      <div role="status" className="space-y-4">
        <p className="rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] px-4 py-3 text-sm text-[var(--brand-ink)]">
          Kata sandi diperbarui. Semua sesi lama sudah dikeluarkan.
        </p>
        <Link
          href="/masuk"
          className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white"
        >
          Masuk dengan kata sandi baru
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="new-password" className="text-sm font-medium">
          Kata sandi baru
        </label>
        <input
          id="new-password"
          name="password"
          type="password"
          required
          minLength={12}
          autoComplete="new-password"
          className={inputClass}
        />
        <p className="mt-1 text-xs text-[var(--muted)]">Minimal 12 karakter.</p>
      </div>
      <div>
        <label htmlFor="confirm-password" className="text-sm font-medium">
          Ulangi kata sandi
        </label>
        <input
          id="confirm-password"
          name="confirmation"
          type="password"
          required
          minLength={12}
          autoComplete="new-password"
          className={inputClass}
        />
      </div>
      {error ? (
        <p
          role="alert"
          className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-3 py-2 text-sm text-[var(--danger)]"
        >
          {error}
        </p>
      ) : null}
      <SubmitButton pending={pending} label="Simpan kata sandi baru" />
    </form>
  );
}

export function VerifyEmailPanel({ token }: { token: string }) {
  const [state, setState] = useState<"pending" | "done" | "error">("pending");
  const [message, setMessage] = useState("Memverifikasi tautan…");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("Tautan verifikasi tidak lengkap.");
      return;
    }
    let active = true;
    async function confirm() {
      try {
        const response = await fetch("/api/auth/verify-email/confirm", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ token }),
        });
        if (!active) return;
        if (!response.ok) {
          const problem = (await response.json().catch(() => ({}))) as {
            title?: string;
          };
          setState("error");
          setMessage(
            problem.title || "Tautan verifikasi tidak valid atau sudah dipakai.",
          );
          return;
        }
        setState("done");
        setMessage("Email berhasil diverifikasi.");
      } catch {
        if (active) {
          setState("error");
          setMessage("Koneksi terputus. Coba lagi nanti.");
        }
      }
    }
    void confirm();
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="space-y-4">
      <p
        role="status"
        className={`rounded-md border px-4 py-3 text-sm ${
          state === "done"
            ? "border-[#cbe6e2] bg-[var(--brand-weak)] text-[var(--brand-ink)]"
            : state === "error"
              ? "border-[#f0c9cb] bg-[#fdf0f0] text-[var(--danger)]"
              : "border-[var(--line)] bg-[var(--bg-alt)] text-[var(--ink-2)]"
        }`}
      >
        {message}
      </p>
      <Link
        href="/app/profil"
        className="inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white"
      >
        Ke profil
      </Link>
    </div>
  );
}