import { NextResponse } from "next/server";

import { readyRedis } from "@/lib/redis";

export const dynamic = "force-dynamic";

const STARTED_AT = Date.now();

export async function GET() {
  const redis = await readyRedis();
  let sessionStore = 0;
  if (redis) {
    try {
      sessionStore = (await redis.ping()) === "PONG" ? 1 : 0;
    } catch {
      sessionStore = 0;
    }
  }
  const body = [
    "# HELP nextjs_info Build metadata for the Next.js frontend.",
    "# TYPE nextjs_info gauge",
    'nextjs_info{version="0.1.0"} 1',
    "# HELP nextjs_uptime_seconds Process uptime.",
    "# TYPE nextjs_uptime_seconds gauge",
    `nextjs_uptime_seconds ${Math.floor((Date.now() - STARTED_AT) / 1000)}`,
    "# HELP nextjs_session_store_up Whether Redis answered the session ping.",
    "# TYPE nextjs_session_store_up gauge",
    `nextjs_session_store_up ${sessionStore}`,
    "",
  ].join("\n");
  return new NextResponse(body, {
    headers: { "content-type": "text/plain; version=0.0.4; charset=utf-8" },
  });
}