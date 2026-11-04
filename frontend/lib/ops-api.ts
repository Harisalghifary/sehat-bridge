import "server-only";

import { ApiError, backendUrl, toApiError } from "@/lib/api";
import { saveOpsSession, type OpsHandle } from "@/lib/ops-session";

export class OpsSessionExpiredError extends Error {}

type Init = {
  method?: string;
  body?: BodyInit | null;
  headers?: Record<string, string>;
};

function adminPath(path: string): string {
  if (path.startsWith("/admin/") || path.startsWith("/users/")) return path;
  return path.startsWith("/") ? `/admin${path}` : `/admin/${path}`;
}

async function fetchOnce(handle: OpsHandle, path: string, init: Init): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("authorization", `Bearer ${handle.data.access_token}`);
  headers.set("accept", "application/json");
  try {
    return await fetch(backendUrl(adminPath(path)), {
      method: init.method ?? "GET",
      headers,
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

export async function refreshOpsTokens(handle: OpsHandle): Promise<boolean> {
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
  return saveOpsSession(handle.sid, handle.data);
}

export async function opsApiResponse(
  handle: OpsHandle,
  path: string,
  init: Init = {},
): Promise<Response> {
  let response = await fetchOnce(handle, path, init);
  if (response.status === 401) {
    const refreshed = await refreshOpsTokens(handle);
    if (!refreshed) throw new OpsSessionExpiredError("Sesi operator berakhir");
    response = await fetchOnce(handle, path, init);
  }
  return response;
}

export async function opsApiRequest<T>(
  handle: OpsHandle,
  path: string,
  init: Init = {},
): Promise<T> {
  const response = await opsApiResponse(handle, path, init);
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}