import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { TenantSuspended } from "@/components/app/TenantSuspended";
import { readSession } from "@/lib/session";

export const metadata: Metadata = {
  title: "Akses ditangguhkan",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function SuspendedPage() {
  const session = await readSession();
  if (!session) redirect("/masuk");

  return <TenantSuspended tenant={session.data.tenant_slug} />;
}