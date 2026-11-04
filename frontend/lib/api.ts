import "server-only";

import { redirect } from "next/navigation";

import { saveSession, type SessionHandle } from "@/lib/session";

const BASE = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export type ApiProblem = {
  code?: string;
  title?: string;
  detail?: string;
  status?: number;
  trace_id?: string | null;
  details?: unknown[];
};

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: string;
  traceId?: string | null;

  constructor(status: number, problem: ApiProblem) {
    super(problem.title ?? "Permintaan gagal");
    this.status = status;
    this.code = problem.code ?? "api_error";
    this.detail = problem.detail;
    this.traceId = problem.trace_id ?? null;
  }
}

export class SessionExpiredError extends Error {}

type Init = {
  method?: string;
  body?: BodyInit | null;
  headers?: Record<string, string>;
};

export function backendUrl(path: string): string {
  return path.startsWith("/api/") ? `${BASE}${path}` : `${BASE}/api/v1${path}`;
}

function headersFor(handle: SessionHandle, init: Init): Headers {
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${handle.data.access_token}`);
  headers.set("x-tenant-id", handle.data.tenant_slug);
  headers.set("accept", "application/json");
  return headers;
}

async function fetchOnce(
  handle: SessionHandle,
  path: string,
  init: Init,
): Promise<Response> {
  try {
    return await fetch(backendUrl(path), {
      method: init.method ?? "GET",
      headers: headersFor(handle, init),
      body: init.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(503, {
      code: "api_unavailable",
      title: "Layanan sedang tidak tersedia",
      detail: "Tidak dapat menghubungi server aplikasi.",
    });
  }
}

export async function toApiError(response: Response): Promise<ApiError> {
  let problem: ApiProblem = {};
  try {
    problem = (await response.json()) as ApiProblem;
  } catch {
    problem = { title: "Permintaan gagal" };
  }
  return new ApiError(response.status, problem);
}

export async function refreshTokens(handle: SessionHandle): Promise<boolean> {
  let response: Response;
  try {
    response = await fetch(backendUrl("/auth/refresh"), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: handle.data.refresh_token }),
      cache: "no-store",
    });
  } catch {
    return false;
  }
  if (!response.ok) return false;

  const payload = (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };
  handle.data.access_token = payload.access_token;
  handle.data.refresh_token = payload.refresh_token;
  return saveSession(handle.sid, handle.data);
}

export async function apiResponse(
  handle: SessionHandle,
  path: string,
  init: Init = {},
): Promise<Response> {
  let response = await fetchOnce(handle, path, init);
  if (response.status === 401) {
    const refreshed = await refreshTokens(handle);
    if (!refreshed) throw new SessionExpiredError("Sesi berakhir");
    response = await fetchOnce(handle, path, init);
  }
  return response;
}

export async function apiRequest<T>(
  handle: SessionHandle,
  path: string,
  init: Init = {},
): Promise<T> {
  const response = await apiResponse(handle, path, init);
  if (!response.ok) {
    const error = await toApiError(response);
    if (error.code === "tenant_inactive") redirect("/app/ditangguhkan");
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export type Readiness = {
  status: string;
  version: string;
  checks: Record<string, string>;
};

export async function fetchReadiness(): Promise<Readiness | null> {
  try {
    const response = await fetch(backendUrl("/health/ready"), {
      cache: "no-store",
    });
    const payload = (await response.json()) as Readiness;
    return payload;
  } catch {
    return null;
  }
}