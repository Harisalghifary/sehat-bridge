"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { StatusBadge } from "@/components/app/StatusBadge";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { FileItem, FileUsage } from "@/lib/types";

const ACCEPTED = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "text/plain",
  "text/csv",
];

const MAX_BYTES = 25 * 1024 * 1024;

type UploadState = {
  key: string;
  name: string;
  size: number;
  progress: number;
  status: "uploading" | "completing" | "error" | "done";
  error?: string;
};

type Problem = { code?: string; detail?: string; title?: string };

function uploadMessage(code: string | undefined, fallback: string): string {
  switch (code) {
    case "file_too_large":
      return "Berkas melebihi batas 25 MB.";
    case "unsupported_media_type":
      return "Tipe berkas tidak didukung. Gunakan PDF, PNG, JPEG, TXT, atau CSV.";
    case "quota_exceeded":
      return "Kuota penyimpanan faskes habis. Hapus berkas lama atau minta penambahan kuota.";
    case "storage_unavailable":
      return "Penyimpanan sedang tidak tersedia. Coba lagi beberapa saat.";
    case "size_mismatch":
    case "content_type_mismatch":
      return "Berkas yang terunggah tidak cocok dengan yang didaftarkan. Coba unggah ulang.";
    case "upload_expired":
      return "Waktu unggah habis. Coba unggah ulang.";
    case "object_not_found":
      return "Berkas tidak ditemukan di penyimpanan. Coba unggah ulang.";
    default:
      return fallback;
  }
}

export function FilesPanel({
  initialFiles,
  usage,
  canSeeAll,
}: {
  initialFiles: FileItem[];
  usage: FileUsage;
  canSeeAll: boolean;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const activeRequests = useRef<Map<string, XMLHttpRequest>>(new Map());

  function updateUpload(key: string, patch: Partial<UploadState>) {
    setUploads((items) =>
      items.map((item) => (item.key === key ? { ...item, ...patch } : item)),
    );
  }

  async function uploadOne(file: File) {
    const key = `${file.name}-${file.size}-${Math.random().toString(36).slice(2)}`;
    setUploads((items) => [
      {
        key,
        name: file.name,
        size: file.size,
        progress: 0,
        status: "uploading",
      },
      ...items,
    ]);

    if (file.size <= 0 || file.size > MAX_BYTES) {
      updateUpload(key, {
        status: "error",
        error: file.size <= 0 ? "Berkas kosong." : "Berkas melebihi batas 25 MB.",
      });
      return;
    }
    if (!ACCEPTED.includes(file.type)) {
      updateUpload(key, {
        status: "error",
        error: "Tipe berkas tidak didukung. Gunakan PDF, PNG, JPEG, TXT, atau CSV.",
      });
      return;
    }

    try {
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
        const problem = (await presign.json().catch(() => ({}))) as Problem;
        updateUpload(key, {
          status: "error",
          error: uploadMessage(problem.code, "Tidak dapat menyiapkan unggahan."),
        });
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

      const xhr = new XMLHttpRequest();
      activeRequests.current.set(key, xhr);
      const uploaded = await new Promise<boolean>((resolve) => {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            updateUpload(key, {
              progress: Math.round((event.loaded / event.total) * 100),
            });
          }
        };
        xhr.onload = () => resolve(xhr.status >= 200 && xhr.status < 300);
        xhr.onerror = () => resolve(false);
        xhr.onabort = () => resolve(false);
        xhr.open("POST", payload.upload.url);
        xhr.send(form);
      });
      activeRequests.current.delete(key);

      if (!uploaded) {
        updateUpload(key, {
          status: "error",
          error:
            "Penyimpanan menolak berkas. Periksa ukuran dan tipe, lalu coba lagi.",
        });
        return;
      }

      updateUpload(key, { status: "completing", progress: 100 });
      const complete = await fetch(`/api/app/files/${payload.file_id}/complete`, {
        method: "POST",
      });
      if (!complete.ok) {
        const problem = (await complete.json().catch(() => ({}))) as Problem;
        updateUpload(key, {
          status: "error",
          error: uploadMessage(problem.code, "Berkas terunggah tetapi gagal diverifikasi."),
        });
        return;
      }

      updateUpload(key, { status: "done", progress: 100 });
      router.refresh();
    } catch {
      updateUpload(key, {
        status: "error",
        error: "Koneksi terputus saat mengunggah. Coba lagi.",
      });
    }
  }

  function handleFiles(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) void uploadOne(file);
  }

  async function download(file: FileItem) {
    setActionError(null);
    const response = await fetch(`/api/app/files/${file.id}/download`);
    if (!response.ok) {
      const problem = (await response.json().catch(() => ({}))) as Problem;
      setActionError(
        uploadMessage(problem.code, "Tidak dapat membuat tautan unduhan."),
      );
      return;
    }
    const payload = (await response.json()) as { url: string };
    window.location.assign(payload.url);
  }

  async function remove(file: FileItem) {
    setActionError(null);
    const response = await fetch(`/api/app/files/${file.id}`, {
      method: "DELETE",
    });
    if (!response.ok && response.status !== 204) {
      const problem = (await response.json().catch(() => ({}))) as Problem;
      setActionError(uploadMessage(problem.code, "Berkas gagal dihapus."));
      return;
    }
    setDeleteTarget(null);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      {actionError ? (
        <p role="alert" className="rounded-md border border-[#f0c9cb] bg-[#fdf0f0] px-4 py-3 text-sm text-[var(--danger)]">
          {actionError}
        </p>
      ) : null}

      <section
        aria-labelledby="upload-title"
        className={`rounded-[10px] border-2 border-dashed bg-white p-6 text-center transition-colors ${
          dragging ? "border-[var(--brand)] bg-[var(--brand-weak)]" : "border-[var(--line)]"
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          handleFiles(event.dataTransfer.files);
        }}
      >
        <h2 id="upload-title" className="text-base font-semibold">
          Tarik berkas ke sini atau pilih
        </h2>
        <p className="mt-1 text-sm text-[var(--ink-2)]">
          PDF, PNG, JPEG, TXT, CSV · maksimum 25 MB per berkas
        </p>
        <input
          ref={inputRef}
          id="file-input"
          type="file"
          multiple
          accept={ACCEPTED.join(",")}
          className="sr-only"
          onChange={(event) => {
            handleFiles(event.target.files);
            event.target.value = "";
          }}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-4 inline-flex min-h-11 items-center rounded-md bg-[var(--brand)] px-5 text-sm font-semibold text-white hover:bg-[var(--brand-ink)]"
        >
          Pilih berkas
        </button>
        <p className="mt-3 text-xs text-[var(--muted)]">
          Sisa kuota: {formatBytes(Math.max(usage.quota_bytes - usage.used_bytes, 0))} dari{" "}
          {formatBytes(usage.quota_bytes)}
        </p>
      </section>

      {uploads.length ? (
        <section aria-labelledby="uploads-title" className="rounded-[10px] border border-[var(--line)] bg-white p-5">
          <h2 id="uploads-title" className="text-sm font-semibold">
            Unggahan sesi ini
          </h2>
          <ul className="mt-3 space-y-3">
            {uploads.map((item) => (
              <li key={item.key} className="rounded-md border border-[var(--line)] p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{item.name}</p>
                    <p className="text-xs text-[var(--muted)]">{formatBytes(item.size)}</p>
                  </div>
                  {item.status === "uploading" || item.status === "completing" ? (
                    <button
                      type="button"
                      onClick={() => {
                        activeRequests.current.get(item.key)?.abort();
                        updateUpload(item.key, { status: "error", error: "Dibatalkan." });
                      }}
                      className="min-h-9 rounded border border-[var(--line)] px-2 text-xs font-medium"
                    >
                      Batal
                    </button>
                  ) : (
                    <span className="text-xs text-[var(--muted)]">
                      {item.status === "done" ? "Selesai" : "Gagal"}
                    </span>
                  )}
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[var(--line)]">
                  <div
                    className="h-1.5 rounded-full bg-[var(--brand)]"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
                {item.error ? (
                  <p role="alert" className="mt-1.5 text-xs text-[var(--danger)]">
                    {item.error}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="files-title">
        <div className="flex items-center justify-between">
          <h2 id="files-title" className="text-sm font-semibold">
            {canSeeAll ? "Berkas tenant" : "Berkas Anda"}
          </h2>
          <span className="text-xs text-[var(--muted)]">{initialFiles.length} berkas</span>
        </div>

        {initialFiles.length === 0 ? (
          <div className="mt-3 rounded-[10px] border border-dashed border-[var(--line)] bg-white p-8 text-center">
            <p className="text-sm font-medium">Belum ada berkas.</p>
            <p className="mt-1 text-sm text-[var(--ink-2)]">
              Unggahan pertama akan muncul di sini dengan status dan tautan unduhan.
            </p>
          </div>
        ) : (
          <>
            <div className="mt-3 hidden overflow-hidden rounded-[10px] border border-[var(--line)] bg-white md:block">
              <table className="w-full text-left text-sm">
                <thead className="bg-[var(--bg-alt)] text-xs uppercase tracking-wide text-[var(--muted)]">
                  <tr>
                    <th scope="col" className="px-4 py-3 font-medium">Nama</th>
                    <th scope="col" className="px-4 py-3 font-medium">Ukuran</th>
                    <th scope="col" className="px-4 py-3 font-medium">Status</th>
                    <th scope="col" className="px-4 py-3 font-medium">Waktu</th>
                    <th scope="col" className="px-4 py-3 text-right font-medium">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {initialFiles.map((file) => (
                    <tr key={file.id}>
                      <td className="max-w-[280px] truncate px-4 py-3 font-medium">{file.filename}</td>
                      <td className="px-4 py-3 text-[var(--ink-2)]">{formatBytes(file.size_bytes)}</td>
                      <td className="px-4 py-3"><StatusBadge status={file.status} /></td>
                      <td className="px-4 py-3 text-[var(--ink-2)]">{formatDateTime(file.created_at)}</td>
                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => void download(file)}
                            disabled={file.status !== "ready"}
                            className="min-h-9 rounded border border-[var(--line)] px-2.5 text-xs font-medium hover:bg-[var(--bg-alt)] disabled:opacity-50"
                          >
                            Unduh
                          </button>
                          {deleteTarget === file.id ? (
                            <>
                              <button
                                type="button"
                                onClick={() => void remove(file)}
                                className="min-h-9 rounded bg-[var(--danger)] px-2.5 text-xs font-semibold text-white"
                              >
                                Yakin hapus
                              </button>
                              <button
                                type="button"
                                onClick={() => setDeleteTarget(null)}
                                className="min-h-9 rounded border border-[var(--line)] px-2.5 text-xs"
                              >
                                Batal
                              </button>
                            </>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setDeleteTarget(file.id)}
                              className="min-h-9 rounded border border-[#f0c9cb] px-2.5 text-xs font-medium text-[var(--danger)] hover:bg-[#fdf0f0]"
                            >
                              Hapus
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <ul className="mt-3 space-y-3 md:hidden">
              {initialFiles.map((file) => (
                <li key={file.id} className="rounded-[10px] border border-[var(--line)] bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="min-w-0 break-words text-sm font-medium">{file.filename}</p>
                    <StatusBadge status={file.status} />
                  </div>
                  <p className="mt-1 text-xs text-[var(--muted)]">
                    {formatBytes(file.size_bytes)} · {formatDateTime(file.created_at)}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void download(file)}
                      disabled={file.status !== "ready"}
                      className="min-h-11 rounded border border-[var(--line)] px-3 text-xs font-medium disabled:opacity-50"
                    >
                      Unduh
                    </button>
                    {deleteTarget === file.id ? (
                      <>
                        <button
                          type="button"
                          onClick={() => void remove(file)}
                          className="min-h-11 rounded bg-[var(--danger)] px-3 text-xs font-semibold text-white"
                        >
                          Yakin hapus
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(null)}
                          className="min-h-11 rounded border border-[var(--line)] px-3 text-xs"
                        >
                          Batal
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(file.id)}
                        className="min-h-11 rounded border border-[#f0c9cb] px-3 text-xs font-medium text-[var(--danger)]"
                      >
                        Hapus
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}