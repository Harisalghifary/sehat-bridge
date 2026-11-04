import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AccessDenied } from "@/components/app/AccessDenied";
import { IntegrationPanel } from "@/components/app/IntegrationPanel";
import { AppPage } from "@/components/app/AppPage";
import { PageHeader } from "@/components/app/PageHeader";
import { ApiError, apiRequest, SessionExpiredError } from "@/lib/api";
import { readSession } from "@/lib/session";
import type {
  IntegrationCredentials,
  JobList,
  SyncJob,
} from "@/lib/types";

export const metadata: Metadata = { title: "Integrasi" };

export default async function IntegrationPage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/integrasi");
  if (session.data.role === "member") return (
      <AppPage next="/app/integrasi">
        <AccessDenied />
      </AppPage>
    );

  try {
    const credentials = await apiRequest<IntegrationCredentials>(
      session,
      "/integrations/satusehat",
    ).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    });
    const jobs = await apiRequest<JobList>(
      session,
      "/integrations/satusehat/jobs?limit=20",
    );

    return (
      <AppPage next="/app/integrasi">
      <div className="space-y-6">
        <PageHeader
          title="Integrasi"
          description="Simpan kredensial per faskes, uji koneksi, lalu antrekan sinkronisasi. Secret tidak pernah ditampilkan kembali."
        />
        <IntegrationPanel
          initialCredentials={credentials}
          initialJobs={jobs.items as SyncJob[]}
        />
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/integrasi");
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
      <AppPage next="/app/integrasi">
        <AccessDenied />
      </AppPage>
    );
    }
    throw error;
  }
}