import "server-only";

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

import { readyRedis } from "@/lib/redis";

export const SESSION_COOKIE = "__Host-sb_sid";
export const SESSION_TTL_SECONDS = 30 * 60;
const COOKIE_MAX_AGE_SECONDS = 12 * 60 * 60;

const PREFIX = "sb:session:";

export type SessionData = {
  user_id: string;
  tenant_id: string;
  tenant_slug: string;
  role: "owner" | "admin" | "member";
  is_platform_admin: boolean;
  access_token: string;
  refresh_token: string;
  csrf: string;
  created_at: string;
};

export type SessionHandle = { sid: string; data: SessionData };

function secret(): string {
  return process.env.SESSION_SECRET ?? "dev-only-session-change-me";
}

function sign(sid: string): string {
  return createHmac("sha256", secret()).update(sid).digest("base64url");
}

function cookieValue(sid: string): string {
  return `${sid}.${sign(sid)}`;
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

export async function createSession(data: SessionData): Promise<string | null> {
  const redis = await readyRedis();
  if (!redis) return null;
  const sid = randomBytes(32).toString("base64url");
  await redis.setex(key(sid), SESSION_TTL_SECONDS, JSON.stringify(data));
  const store = await cookies();
  store.set(SESSION_COOKIE, cookieValue(sid), {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_SECONDS,
  });
  return sid;
}

export async function readSession(): Promise<SessionHandle | null> {
  const store = await cookies();
  const raw = store.get(SESSION_COOKIE)?.value;
  if (!raw) return null;
  const sid = parseCookie(raw);
  if (!sid) return null;

  const redis = await readyRedis();
  if (!redis) return null;
  const stored = await redis.get(key(sid));
  if (!stored) return null;

  try {
    const data = JSON.parse(stored) as SessionData;
    await redis.expire(key(sid), SESSION_TTL_SECONDS);
    return { sid, data };
  } catch {
    await redis.del(key(sid));
    return null;
  }
}

export async function saveSession(
  sid: string,
  data: SessionData,
): Promise<boolean> {
  const redis = await readyRedis();
  if (!redis) return false;
  await redis.setex(key(sid), SESSION_TTL_SECONDS, JSON.stringify(data));
  return true;
}

export async function destroySession(sid?: string): Promise<void> {
  if (sid) {
    const redis = await readyRedis();
    if (redis) await redis.del(key(sid));
  }
  const store = await cookies();
  store.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
}

export function roleAllows(
  role: SessionData["role"],
  allowed: readonly SessionData["role"][],
): boolean {
  return allowed.includes(role);
}