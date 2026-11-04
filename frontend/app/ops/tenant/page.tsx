import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { OpsPage } from "@/components/ops/OpsPage";
import { TenantConsole } from "@/components/ops/TenantConsole";
import { ApiError } from "@/lib/api";
import { opsApiRequest, OpsSessionExpiredError } from "@/lib/ops-api";
import { readOpsSession } from "@/lib/ops-session";
import type { OpsTenant, OpsTenantList } from "@/lib/ops-types";

export const metadata: Metadata = {
  title: "Tenant · Operator",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

export default async function OpsTenantPage() {
  const session = await readOpsSession();
  if (!session) redirect("/ops/masuk?next=/ops/tenant");

  try {
    const data = await opsApiRequest<OpsTenantList>(session, "/admin/tenants");
    return (
      <OpsPage next="/ops/tenant">
        <TenantConsole initial={data.items as OpsTenant[]} />
      </OpsPage>
    );
  } catch (error) {
    if (error instanceof OpsSessionExpiredError) {
      redirect("/ops/masuk?next=/ops/tenant");
    }
    if (error instanceof ApiError && error.status === 403) {
      redirect("/ops/masuk");
    }
    throw error;
  }
}