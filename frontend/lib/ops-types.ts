export type OpsTenant = {
  slug: string;
  name: string;
  status: "provisioning" | "active" | "suspended" | "failed" | string;
  plan: string;
  members: number;
  owner_email: string | null;
  failure_note: string | null;
  created_at: string;
  updated_at: string;
};

export type OpsTenantDetail = OpsTenant & {
  queued_jobs: number;
  failed_jobs: number;
};

export type OpsTenantList = { items: OpsTenant[] };

export type ProvisionStep = {
  key: string;
  label: string;
  status: "done" | "failed";
};

export type ProvisionResponse = {
  tenant: OpsTenantDetail;
  owner_email: string;
  steps: ProvisionStep[];
};

export type AuditRow = {
  id: number;
  tenant_slug: string | null;
  tenant_name: string | null;
  actor_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type AuditList = {
  items: AuditRow[];
  total: number;
  limit: number;
  offset: number;
};

export type OpsHealth = {
  status: "ok" | "degraded" | string;
  version: string;
  uptime_seconds: number;
  checks: Record<string, "ok" | "error">;
  queue: { queued: number; running: number; failed: number; dead: number };
  tenants: {
    active: number;
    suspended: number;
    provisioning: number;
    failed: number;
  };
};