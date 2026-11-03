"use client";

import Link from "next/link";
import { useRef, useState } from "react";

type State =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success" }
  | { kind: "error"; message: string };

const inputClass =
  "mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-3 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--muted)] focus:border-[var(--brand)] focus:outline-none";

export function DemoForm() {
  const startedAt = useRef(Date.now());
  const [state, setState] = useState<State>({ kind: "idle" });

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.kind === "submitting") return;

    const form = event.currentTarget;
    const data = new FormData(form);
    setState({ kind: "submitting" });

    try {
      const response = await fetch("/api/lead", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: data.get("name"),
          email: data.get("email"),
          facility_name: data.get("facility_name"),
          facility_type: data.get("facility_type") || null,
          city: data.get("city") || null,
          phone: data.get("phone") || null,
          message: data.get("message") || null,
          website: data.get("website") ?? "",
          elapsed_ms: Date.now() - startedAt.current,
        }),
      });

      if (response.status === 429) {
        setState({
          kind: "error",
          message:
            "Terlalu banyak pengiriman dari jaringan ini. Coba lagi dalam satu jam atau hubungi kami lewat WhatsApp.",
        });
        return;
      }

      if (!response.ok) {
        let detail =
          "Formulir belum bisa dikirim. Periksa kembali isian lalu coba lagi.";
        try {
          const problem = (await response.json()) as { detail?: string };
          if (problem.detail) detail = problem.detail;
        } catch {
          // Keep the generic message when the upstream body is not JSON.
        }
        setState({ kind: "error", message: detail });
        return;
      }

      setState({ kind: "success" });
      form.reset();
    } catch {
      setState({
        kind: "error",
        message:
          "Koneksi terputus sebelum formulir terkirim. Periksa jaringan lalu coba lagi.",
      });
    }
  }

  if (state.kind === "success") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="rounded-[10px] border border-[#cbe6e2] bg-[var(--brand-weak)] p-8"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand-ink)]">
          Terkirim
        </p>
        <h2 className="h2 mt-3">Terima kasih. Kami akan menghubungi Anda.</h2>
        <p className="mt-4 text-sm leading-6 text-[var(--ink-2)]">
          Tim akan membalas dalam 1–2 hari kerja. Sertakan jam yang nyaman bila
          Anda ingin dihubungi lewat telepon.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            href="/faq"
            className="inline-flex min-h-11 items-center rounded-md border border-[var(--line)] bg-white px-5 py-3 text-sm font-semibold"
          >
            Baca FAQ
          </Link>
          <Link
            href="/"
            className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 py-3 text-sm font-semibold text-white"
          >
            Kembali ke beranda
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate={false} aria-describedby="demo-note">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Nama" htmlFor="name">
          <input
            id="name"
            name="name"
            required
            minLength={2}
            maxLength={200}
            autoComplete="name"
            className={inputClass}
            placeholder="dr. Sari"
          />
        </Field>
        <Field label="Email" htmlFor="email">
          <input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            className={inputClass}
            placeholder="sari@klinik.example"
          />
        </Field>
        <Field label="Nama faskes" htmlFor="facility_name">
          <input
            id="facility_name"
            name="facility_name"
            required
            minLength={2}
            maxLength={200}
            autoComplete="organization"
            className={inputClass}
            placeholder="Klinik Sehat Bersama"
          />
        </Field>
        <Field label="Jenis faskes" htmlFor="facility_type">
          <select
            id="facility_type"
            name="facility_type"
            className={inputClass}
            defaultValue=""
          >
            <option value="">Pilih jenis</option>
            <option value="klinik">Klinik</option>
            <option value="rumah_sakit">Rumah sakit</option>
            <option value="lab">Laboratorium</option>
            <option value="apotek">Apotek</option>
            <option value="lainnya">Lainnya</option>
          </select>
        </Field>
        <Field label="Kota" htmlFor="city" optional>
          <input
            id="city"
            name="city"
            maxLength={120}
            autoComplete="address-level2"
            className={inputClass}
            placeholder="Bandung"
          />
        </Field>
        <Field label="Telepon" htmlFor="phone" optional>
          <input
            id="phone"
            name="phone"
            maxLength={40}
            autoComplete="tel"
            className={inputClass}
            placeholder="0812…"
          />
        </Field>
      </div>

      <div className="mt-4">
        <Field label="Pesan" htmlFor="message" optional>
          <textarea
            id="message"
            name="message"
            rows={4}
            maxLength={2000}
            className={inputClass}
            placeholder="Bagian mana yang ingin Anda lihat lebih dulu?"
          />
        </Field>
      </div>

      <div
        aria-hidden="true"
        className="absolute -left-[9999px] top-auto h-px w-px overflow-hidden"
      >
        <label htmlFor="website">Website</label>
        <input
          id="website"
          name="website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <p id="demo-note" className="mt-4 text-xs leading-5 text-[var(--muted)]">
        Dengan mengirim formulir, Anda setuju kami menyimpan data kontak untuk
        menindaklanjuti permintaan demo. Baca{" "}
        <Link href="/privasi" className="underline underline-offset-4">
          kebijakan privasi
        </Link>
        .
      </p>

      {state.kind === "error" ? (
        <p
          role="alert"
          className="mt-4 rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-4 py-3 text-sm text-[var(--danger)]"
        >
          {state.message}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={state.kind === "submitting"}
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-md bg-[var(--brand)] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-ink)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {state.kind === "submitting" ? "Mengirim…" : "Kirim permintaan demo"}
      </button>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  optional,
  children,
}: {
  label: string;
  htmlFor: string;
  optional?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
        {optional ? (
          <span className="ml-1 text-xs font-normal text-[var(--muted)]">
            (opsional)
          </span>
        ) : null}
      </label>
      {children}
    </div>
  );
}