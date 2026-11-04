import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AccessDenied } from "@/components/app/AccessDenied";
import { MembersTable } from "@/components/app/MembersTable";
import { AppPage } from "@/components/app/AppPage";
import { PageHeader } from "@/components/app/PageHeader";
import { ApiError, apiRequest, SessionExpiredError } from "@/lib/api";
import { readSession } from "@/lib/session";
import type { MemberList } from "@/lib/types";

export const metadata: Metadata = { title: "Anggota" };

export default async function MembersPage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/anggota");
  if (session.data.role === "member") return (
      <AppPage next="/app/anggota">
        <AccessDenied />
      </AppPage>
    );

  try {
    const data = await apiRequest<MemberList>(session, "/users?limit=100");
    const members =
      session.data.role === "owner"
        ? data.items
        : data.items.filter((member) => member.role !== "owner");

    return (
      <AppPage next="/app/anggota">
      <div className="space-y-6">
        <PageHeader
          title="Anggota"
          description="Kelola peran anggota faskes. Perubahan berlaku di server dan dicatat pada audit."
        />
        <MembersTable
          initialMembers={members}
          actorRole={session.data.role}
          actorId={session.data.user_id}
        />
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/anggota");
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
      <AppPage next="/app/anggota">
        <AccessDenied />
      </AppPage>
    );
    }
    throw error;
  }
}