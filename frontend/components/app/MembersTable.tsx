"use client";

import { useState } from "react";

import { formatDate, roleLabel } from "@/lib/format";
import type { Member } from "@/lib/types";

type Problem = { code?: string; detail?: string; title?: string };

export function MembersTable({
  initialMembers,
  actorRole,
  actorId,
}: {
  initialMembers: Member[];
  actorRole: "owner" | "admin" | "member";
  actorId: string;
}) {
  const [members, setMembers] = useState(initialMembers);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<{ id: string; message: string } | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function copyInvite() {
    const origin =
      typeof window === "undefined" ? "aplikasi" : window.location.origin;
    const text = [
      "Undangan akses Sehat Bridge",
      "",
      `Buka ${origin}/masuk dan gunakan kode faskes serta akun yang diberikan admin.`,
      "Pendaftaran publik belum dibuka; akun dibuat oleh admin faskes.",
      "Bantuan: halo@sehatbridge.dev",
    ].join("\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  async function changeRole(member: Member, role: string) {
    setError(null);
    setSaved(null);
    setPending(member.id);
    try {
      const response = await fetch(`/api/app/users/${member.id}/role`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ role }),
      });
      if (!response.ok) {
        const problem = (await response.json().catch(() => ({}))) as Problem;
        const message =
          problem.code === "last_owner"
            ? "Owner terakhir tidak dapat diturunkan perannya."
            : problem.code === "insufficient_role"
              ? "Peran Anda tidak mengizinkan perubahan ini."
              : problem.detail || problem.title || "Peran gagal diubah.";
        setError({ id: member.id, message });
        return;
      }
      const updated = (await response.json()) as Member;
      setMembers((items) =>
        items.map((item) => (item.id === member.id ? updated : item)),
      );
      setSaved(member.id);
    } catch {
      setError({ id: member.id, message: "Koneksi terputus. Coba lagi." });
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="rounded-[10px] border border-[var(--line)] bg-[var(--bg-alt)] p-4 text-sm text-[var(--ink-2)]">
        <p className="font-medium text-[var(--ink)]">Undangan anggota</p>
        <p className="mt-1">
          Alur undangan lewat email belum tersedia. Untuk menambah anggota,
          hubungi admin platform dengan alamat email dan peran yang diinginkan.
        </p>
        <a
          href="mailto:halo@sehatbridge.dev?subject=Permintaan%20undangan%20anggota"
          className="mt-2 inline-flex min-h-9 items-center text-sm font-semibold text-[var(--brand)] underline underline-offset-4"
        >
          Kirim permintaan lewat email
        </a>
        <button
          type="button"
          onClick={() => void copyInvite()}
          className="ml-3 mt-2 inline-flex min-h-11 items-center rounded-md border border-[var(--line)] px-3 text-sm font-semibold"
        >
          {copied ? "Teks undangan disalin" : "Salin teks undangan"}
        </button>
        <p aria-live="polite" className="sr-only">
          {copied ? "Teks undangan disalin ke papan klip." : ""}
        </p>
      </div>

      <div className="hidden overflow-hidden rounded-[10px] border border-[var(--line)] bg-white md:block">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--bg-alt)] text-xs uppercase tracking-wide text-[var(--muted)]">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">Anggota</th>
              <th scope="col" className="px-4 py-3 font-medium">Peran</th>
              <th scope="col" className="px-4 py-3 font-medium">Bergabung</th>
              <th scope="col" className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {members.map((member) => (
              <tr key={member.id}>
                <td className="px-4 py-3">
                  <p className="font-medium">
                    {member.display_name || member.email}
                    {member.id === actorId ? " (Anda)" : ""}
                  </p>
                  {member.display_name ? (
                    <p className="text-xs text-[var(--muted)]">{member.email}</p>
                  ) : null}
                </td>
                <td className="px-4 py-3">
                  <select
                    aria-label={`Peran ${member.email}`}
                    value={member.role}
                    disabled={pending === member.id}
                    onChange={(event) => void changeRole(member, event.target.value)}
                    className="min-h-10 rounded-md border border-[var(--line)] bg-white px-2 text-sm"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                    {actorRole === "owner" ? (
                      <option value="owner">Owner</option>
                    ) : null}
                  </select>
                  {error?.id === member.id ? (
                    <p role="alert" className="mt-1 text-xs text-[var(--danger)]">
                      {error.message}
                    </p>
                  ) : null}
                  {saved === member.id ? (
                    <p className="mt-1 text-xs text-[var(--ok)]">Peran tersimpan.</p>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-[var(--ink-2)]">
                  {formatDate(member.joined_at)}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-[var(--bg-alt)] px-2 py-1 text-xs font-medium">
                    {member.is_verified ? "Terverifikasi" : "Belum verifikasi"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="space-y-3 md:hidden">
        {members.map((member) => (
          <li key={member.id} className="rounded-[10px] border border-[var(--line)] bg-white p-4">
            <p className="break-words text-sm font-semibold">
              {member.display_name || member.email}
              {member.id === actorId ? " (Anda)" : ""}
            </p>
            <p className="mt-1 break-words text-xs text-[var(--muted)]">{member.email}</p>
            <p className="mt-2 text-xs text-[var(--ink-2)]">
              {roleLabel(member.role)} · bergabung {formatDate(member.joined_at)}
            </p>
            <label className="mt-3 block text-xs font-medium">
              Ubah peran
              <select
                value={member.role}
                disabled={pending === member.id}
                onChange={(event) => void changeRole(member, event.target.value)}
                className="mt-1 min-h-11 w-full rounded-md border border-[var(--line)] bg-white px-2 text-sm"
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                {actorRole === "owner" ? <option value="owner">Owner</option> : null}
              </select>
            </label>
            {error?.id === member.id ? (
              <p role="alert" className="mt-1 text-xs text-[var(--danger)]">
                {error.message}
              </p>
            ) : null}
            {saved === member.id ? (
              <p className="mt-1 text-xs text-[var(--ok)]">Peran tersimpan.</p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}