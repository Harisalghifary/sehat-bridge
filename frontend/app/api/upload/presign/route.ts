import { apiResponse, SessionExpiredError } from "@/lib/api";
import {
  guardOrigin,
  problem,
  proxyResponse,
  requireSessionForRoute,
} from "@/lib/http";
import { destroySession } from "@/lib/session";

export async function POST(request: Request) {
  const originError = guardOrigin(request);
  if (originError) return originError;

  const { session, response } = await requireSessionForRoute();
  if (!session) return response;

  try {
    const upstream = await apiResponse(session, "/files/presign-upload", {
      method: "POST",
      body: await request.text(),
      headers: { "content-type": "application/json" },
    });
    return proxyResponse(upstream);
  } catch (error) {
    if (error instanceof SessionExpiredError) {
      await destroySession(session.sid);
      return problem(401, "session_expired", "Sesi berakhir, silakan masuk lagi");
    }
    return problem(503, "storage_unavailable", "Penyimpanan sedang tidak tersedia");
  }
}