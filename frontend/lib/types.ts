export type MeResponse = {
  id: string;
  email: string;
  is_verified: boolean;
  is_platform_admin: boolean;
  membership: {
    role: "owner" | "admin" | "member";
    tenant: { id: string; slug: string; name: string };
  } | null;
  profile: {
    display_name: string;
    timezone: string;
    avatar_file_id: string | null;
  } | null;
};

export type FileItem = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "uploading" | "ready" | "deleted";
  sha256: string | null;
  owner_user_id: string;
  created_at: string;
  completed_at: string | null;
};

export type FileList = {
  items: FileItem[];
  next_cursor: string | null;
  has_more: boolean;
};

export type FileUsage = {
  files: number;
  used_bytes: number;
  quota_bytes: number;
};

export type Member = {
  id: string;
  email: string;
  role: "owner" | "admin" | "member";
  display_name: string | null;
  is_verified: boolean;
  joined_at: string;
};

export type MemberList = {
  items: Member[];
  next_cursor: string | null;
  has_more: boolean;
};

export type IntegrationCredentials = {
  provider: string;
  status: "unverified" | "connected" | "error";
  has_secret: boolean;
  client_id: string | null;
  organization_id: string | null;
  base_url: string;
  last_verified_at: string | null;
  last_error: string | null;
  mode: string;
};

export type SyncJob = {
  id: string;
  kind: "organization" | "patient";
  status: "queued" | "running" | "done" | "failed" | "dead";
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  fhir_id: string | null;
};

export type SyncJobDetail = SyncJob & {
  response_body: Record<string, unknown> | null;
};

export type JobList = {
  items: SyncJob[];
  next_cursor: string | null;
  has_more: boolean;
};