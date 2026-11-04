import "server-only";

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

import { readyRedis } from "@/lib/redis";

export const OPS_COOKIE = "__Host-sb_ops";
export const OPS_TTL_SECONDS = 30 * 60;
const COOKIE_MAX_AGE_SECONDS = 12 * 60 * 60;
const PREFIX = "sb:ops:";

export type OpsSessionData = {
  user_id: string;
  email: string;
  access_token: string;
  refresh_token: string;
  created_at: string;
};

export type OpsHandle = { sid: string; data: OpsSessionData };

function secret(): string {
  return process.env.SESSION_SECRET ?? "dev-only-session-change-me";
}

function sign(sid: string): string {
  return createHmac("sha256", secret()).update(sid).digest("base64url");
}

function parseCookie(value: string): string | null {
  const [sid, signature] = value.split(".");
  if (!sid || !signature) return null;
  const expected = sign(sid);
  const left = Buffer.from(signature);
  const right = Buffer.from(expected);
  if (left.length !== right.length) return null;
  return timingSafeEqual(left, right) ? sid : null;
}

function key(sid: string): string {
  return `${PREFIX}${sid}`;
}

export async function createOpsSession(data: OpsSessionData): Promise<boolean> {
  const redis = await readyRedis();
  if (!redis) return false;
  const sid = randomBytes(32).toString("base64url");
  await redis.setex(key(sid), OPS_TTL_SECONDS, JSON.stringify(data));
  const store = await cookies();
  store.set(OPS_COOKIE, `${sid}.${sign(sid)}`, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_SECONDS,
  });
  return true;
}

export async function readOpsSession(): Promise<OpsHandle | null> {
  const store = await cookies();
  const raw = store.get(OPS_COOKIE)?.value;
  if (!raw) return null;
  const sid = parseCookie(raw);
  if (!sid) return null;

  const redis = await readyRedis();
  if (!redis) return null;
  const stored = await redis.get(key(sid));
  if (!stored) return null;

  try {
    const data = JSON.parse(stored) as OpsSessionData;
    await redis.expire(key(sid), OPS_TTL_SECONDS);
    return { sid, data };
  } catch {
    await redis.del(key(sid));
    return null;
  }
}

export async function saveOpsSession(
  sid: string,
  data: OpsSessionData,
): Promise<boolean> {
  const redis = await readyRedis();
  if (!redis) return false;
  await redis.setex(key(sid), OPS_TTL_SECONDS, JSON.stringify(data));
  return true;
}

export async function destroyOpsSession(sid?: string): Promise<void> {
  if (sid) {
    const redis = await readyRedis();
    if (redis) await redis.del(key(sid));
  }
  const store = await cookies();
  store.set(OPS_COOKIE, "", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}