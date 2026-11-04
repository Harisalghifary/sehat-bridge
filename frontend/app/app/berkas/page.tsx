import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AppPage } from "@/components/app/AppPage";
import { PageHeader } from "@/components/app/PageHeader";
import { FilesPanel } from "@/components/app/FilesPanel";
import { ApiError, apiRequest, SessionExpiredError } from "@/lib/api";
import { readSession } from "@/lib/session";
import type { FileList, FileUsage } from "@/lib/types";

export const metadata: Metadata = { title: "Berkas" };

export default async function FilesPage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/berkas");

  try {
    const [files, usage] = await Promise.all([
      apiRequest<FileList>(session, "/files?limit=50"),
      apiRequest<FileUsage>(session, "/files/usage"),
    ]);

    return (
      <AppPage next="/app/berkas">
      <div className="space-y-6">
        <PageHeader
          title="Berkas"
          description="Unggah langsung ke penyimpanan objek. Berkas diverifikasi ukuran dan tipenya sebelum ditandai siap."
        />
        <FilesPanel
          initialFiles={files.items}
          usage={usage}
          canSeeAll={session.data.role !== "member"}
        />
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/berkas");
    }
    if (error instanceof ApiError && error.code === "storage_unavailable") {
      return (
        <AppPage next="/app/berkas">
          <div className="space-y-6">
            <PageHeader title="Berkas" />
            <div role="alert" className="rounded-[10px] border border-[#f0dfbc] bg-[#fff6e5] p-6 text-sm text-[var(--warn)]">
              Penyimpanan sedang tidak tersedia. Halaman lain tetap dapat dipakai.
            </div>
          </div>
        </AppPage>
      );
    }
    throw error;
  }
}