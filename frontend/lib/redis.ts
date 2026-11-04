import "server-only";

import Redis from "ioredis";

const globalForRedis = globalThis as unknown as { sbRedis?: Redis };

function client(): Redis {
  if (!globalForRedis.sbRedis) {
    globalForRedis.sbRedis = new Redis(
      process.env.REDIS_DSN ?? "redis://localhost:6379/0",
      {
        lazyConnect: true,
        connectTimeout: 2000,
        maxRetriesPerRequest: 1,
        enableOfflineQueue: false,
      },
    );
    globalForRedis.sbRedis.on("error", () => {
      // Session reads fail closed at the call site; never crash the process.
    });
  }
  return globalForRedis.sbRedis;
}

export async function readyRedis(): Promise<Redis | null> {
  const redis = client();
  if (redis.status === "wait") {
    try {
      await redis.connect();
    } catch {
      return null;
    }
  }
  return redis.status === "ready" ? redis : null;
}