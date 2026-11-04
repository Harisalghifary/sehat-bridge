import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { AppPage } from "@/components/app/AppPage";
import { EmailVerification } from "@/components/app/EmailVerification";
import { PageHeader } from "@/components/app/PageHeader";
import { ProfileForm } from "@/components/app/ProfileForm";
import { ApiError, apiRequest, SessionExpiredError } from "@/lib/api";
import { readSession } from "@/lib/session";
import type { MeResponse } from "@/lib/types";

export const metadata: Metadata = { title: "Profil" };

export default async function ProfilePage() {
  const session = await readSession();
  if (!session) redirect("/masuk?next=/app/profil");

  try {
    const me = await apiRequest<MeResponse>(session, "/users/me");
    let avatarUrl: string | null = null;
    if (me.profile?.avatar_file_id) {
      avatarUrl = await apiRequest<{ url: string }>(
        session,
        `/files/${me.profile.avatar_file_id}/download`,
      )
        .then((data) => data.url)
        .catch((error: unknown) => {
          if (error instanceof ApiError && error.status === 404) return null;
          throw error;
        });
    }

    return (
      <AppPage next="/app/profil">
      <div className="space-y-6">
        <PageHeader
          title="Profil"
          description="Perbarui nama tampilan, zona waktu, dan avatar. Perubahan disimpan ke profil tenant Anda."
        />
        <ProfileForm
          email={me.email}
          displayName={me.profile?.display_name || me.email}
          timezone={me.profile?.timezone ?? "UTC"}
          avatarFileId={me.profile?.avatar_file_id ?? null}
          avatarUrl={avatarUrl}
        />
        <EmailVerification email={me.email} verified={me.is_verified} />
      </div>
      </AppPage>
    );
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      redirect("/masuk?next=/app/profil");
    }
    throw error;
  }
}