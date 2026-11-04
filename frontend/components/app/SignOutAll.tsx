"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function SignOutAll() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function signOut() {
    setPending(true);
    setError(null);
    try {
      const response = await fetch("/api/session", {
        method: "DELETE",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ all_sessions: true }),
      });
      if (!response.ok) {
        setError("Sesi gagal diakhiri. Coba lagi.");
        return;
      }
      router.replace("/masuk");
      router.refresh();
    } catch {
      setError("Koneksi terputus. Coba lagi.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      {confirming ? (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void signOut()}
            disabled={pending}
            className="inline-flex min-h-11 items-center rounded-md bg-[var(--danger)] px-4 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pending ? "Mengakhiri…" : "Ya, akhiri semua sesi"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            disabled={pending}
            className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-4 text-sm font-medium"
          >
            Batal
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="inline-flex min-h-11 items-center rounded-md border border-[#f0c9cb] px-4 text-sm font-semibold text-[var(--danger)] hover:bg-[#fdf0f0]"
        >
          Keluar dari semua sesi
        </button>
      )}
      {error ? (
        <p role="alert" className="mt-2 text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
    </div>
  );
}