import "server-only";

import { problem } from "@/lib/http";
import { readOpsSession } from "@/lib/ops-session";

export async function requireOpsSessionForRoute() {
  const session = await readOpsSession();
  if (!session) {
    return {
      session: null,
      response: problem(401, "session_required", "Sesi operator tidak ditemukan"),
    };
  }
  return { session, response: null };
}