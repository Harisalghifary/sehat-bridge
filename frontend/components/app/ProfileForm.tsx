"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

const TIMEZONES = [
  "Asia/Jakarta",
  "Asia/Pontianak",
  "Asia/Makassar",
  "Asia/Jayapura",
  "UTC",
];

export function ProfileForm({
  email,
  displayName,
  timezone,
  avatarFileId,
  avatarUrl,
}: {
  email: string;
  displayName: string;
  timezone: string;
  avatarFileId: string | null;
  avatarUrl: string | null;
}) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [avatarPending, setAvatarPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [avatarId, setAvatarId] = useState(avatarFileId);
  const [avatarPreview, setAvatarPreview] = useState(avatarUrl);

  async function saveProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/app/users/me", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          display_name: String(data.get("display_name") ?? "").trim(),
          timezone: String(data.get("timezone") ?? "UTC"),
        }),
      });
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as {
          detail?: string;
          code?: string;
        };
        setError(
          problem.code === "invalid_timezone"
            ? "Zona waktu tidak dikenali."
            : problem.detail || "Profil gagal disimpan.",
        );
        return;
      }
      setMessage("Profil tersimpan.");
      router.refresh();
    } catch {
      setError("Koneksi terputus. Coba lagi.");
    } finally {
      setPending(false);
    }
  }

  async function uploadAvatar(file: File) {
    setAvatarPending(true);
    setError(null);
    setMessage(null);
    try {
      if (file.size <= 0 || file.size > 5 * 1024 * 1024) {
        setError("Avatar maksimum 5 MB.");
        return;
      }
      if (!["image/png", "image/jpeg"].includes(file.type)) {
        setError("Avatar harus PNG atau JPEG.");
        return;
      }

      const presign = await fetch("/api/upload/presign", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type,
          size_bytes: file.size,
        }),
      });
      if (!presign.ok) {
        setError("Tidak dapat menyiapkan unggahan avatar.");
        return;
      }
      const payload = (await presign.json()) as {
        file_id: string;
        upload: { url: string; fields: Record<string, string> };
      };

      const form = new FormData();
      for (const [name, value] of Object.entries(payload.upload.fields)) {
        form.append(name, value);
      }
      form.append("file", file);
      const uploaded = await fetch(payload.upload.url, {
        method: "POST",
        body: form,
      });
      if (!uploaded.ok) {
        setError("Penyimpanan menolak avatar. Periksa ukuran dan tipe.");
        return;
      }

      const complete = await fetch(`/api/app/files/${payload.file_id}/complete`, {
        method: "POST",
      });
      if (!complete.ok) {
        setError("Avatar terunggah tetapi gagal diverifikasi.");
        return;
      }

      const updated = await fetch("/api/app/users/me", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ avatar_file_id: payload.file_id }),
      });
      if (!updated.ok) {
        setError("Avatar terunggah tetapi profil gagal diperbarui.");
        return;
      }

      const link = await fetch(`/api/app/files/${payload.file_id}/download`);
      if (link.ok) {
        const data = (await link.json()) as { url: string };
        setAvatarPreview(data.url);
      }
      setAvatarId(payload.file_id);
      setMessage("Avatar diperbarui.");
      router.refresh();
    } catch {
      setError("Koneksi terputus saat mengunggah avatar.");
    } finally {
      setAvatarPending(false);
    }
  }

  async function removeAvatar() {
    setAvatarPending(true);
    setError(null);
    try {
      const response = await fetch("/api/app/users/me", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ avatar_file_id: null }),
      });
      if (!response.ok) {
        setError("Avatar gagal dihapus.");
        return;
      }
      setAvatarId(null);
      setAvatarPreview(null);
      setMessage("Avatar dihapus.");
      router.refresh();
    } finally {
      setAvatarPending(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
      <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
        <h2 className="text-sm font-semibold">Avatar</h2>
        <div className="mt-4 flex items-center gap-4">
          {avatarPreview ? (
            // Presigned MinIO URL; dimensions are fixed to avoid layout shift.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarPreview}
              alt="Avatar profil"
              width={72}
              height={72}
              className="size-18 rounded-full border border-[var(--line)] object-cover"
            />
          ) : (
            <span className="grid size-18 place-items-center rounded-full bg-[var(--brand-weak)] text-xl font-semibold text-[var(--brand-ink)]">
              {email.slice(0, 2).toUpperCase()}
            </span>
          )}
          <div className="flex flex-col gap-2">
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void uploadAvatar(file);
                event.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              disabled={avatarPending}
              className="min-h-11 rounded-md border border-[var(--line)] px-4 text-sm font-semibold disabled:opacity-60"
            >
              {avatarPending ? "Mengunggah…" : "Pilih gambar"}
            </button>
            {avatarId ? (
              <button
                type="button"
                onClick={() => void removeAvatar()}
                disabled={avatarPending}
                className="min-h-9 rounded-md px-2 text-left text-xs font-medium text-[var(--danger)]"
              >
                Hapus avatar
              </button>
            ) : null}
          </div>
        </div>
        <p className="mt-4 text-xs leading-5 text-[var(--muted)]">
          PNG atau JPEG, maksimum 5 MB. Avatar disimpan sebagai berkas tenant.
        </p>
      </section>

      <section className="rounded-[10px] border border-[var(--line)] bg-white p-5">
        <h2 className="text-sm font-semibold">Data profil</h2>
        {message ? (
          <p role="status" className="mt-3 rounded-md border border-[#cbe6e2] bg-[var(--brand-weak)] px-3 py-2 text-sm text-[var(--brand-ink)]">
            {message}
          </p>
        ) : null}
        {error ? (
          <p role="alert" className="mt-3 rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-3 py-2 text-sm text-[var(--danger)]">
            {error}
          </p>
        ) : null}

        <form onSubmit={saveProfile} className="mt-4 space-y-4">
          <div>
            <label htmlFor="profile-email" className="text-sm font-medium">
              Email
            </label>
            <input
              id="profile-email"
              value={email}
              readOnly
              className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-[var(--bg-alt)] px-3 text-sm text-[var(--ink-2)]"
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              Email tidak dapat diubah sendiri.
            </p>
          </div>
          <div>
            <label htmlFor="display_name" className="text-sm font-medium">
              Nama tampilan
            </label>
            <input
              id="display_name"
              name="display_name"
              required
              maxLength={120}
              defaultValue={displayName}
              className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] px-3 text-sm"
            />
          </div>
          <div>
            <label htmlFor="timezone" className="text-sm font-medium">
              Zona waktu
            </label>
            <select
              id="timezone"
              name="timezone"
              defaultValue={timezone}
              className="mt-1.5 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-3 text-sm"
            >
              {TIMEZONES.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={pending}
            className="inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pending ? "Menyimpan…" : "Simpan profil"}
          </button>
        </form>
      </section>
    </div>
  );
}