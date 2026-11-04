"use client";

import { useState } from "react";

export function EmailVerification({
  email,
  verified,
}: {
  email: string;
  verified: boolean;
}) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (pending) return;
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/app/auth/verify-email", {
        method: "POST",
      });
      if (!response.ok) {
        setError("Tautan verifikasi tidak dapat dikirim sekarang.");
        return;
      }
      setMessage("Tautan verifikasi dikirim. Periksa kotak masuk dan folder spam.");
    } catch {
      setError("Koneksi terputus. Coba lagi sesaat.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section
      aria-labelledby="email-verification-title"
      className="rounded-[10px] border border-[var(--line)] bg-white p-5"
    >
      <h2 id="email-verification-title" className="text-sm font-semibold">
        Verifikasi email
      </h2>
      <p className="mt-1 text-sm leading-6 text-[var(--ink-2)]">
        {verified
          ? `${email} sudah diverifikasi.`
          : `${email} belum diverifikasi. Verifikasi membantu pemulihan akun.`}
      </p>
      {!verified ? (
        <button
          type="button"
          onClick={() => void send()}
          disabled={pending}
          className="mt-3 inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-4 text-sm font-semibold disabled:opacity-60"
        >
          {pending ? "Mengirim…" : "Kirim tautan verifikasi"}
        </button>
      ) : null}
      {message ? (
        <p role="status" className="mt-3 text-sm text-[var(--brand-ink)]">
          {message}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
    </section>
  );
}