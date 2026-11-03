import type { MetadataRoute } from "next";

import { site } from "@/lib/site";

const base = site.url.replace(/\/$/, "");

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/app/", "/ops/", "/masuk"],
    },
    sitemap: `${base}/sitemap.xml`,
    host: base,
  };
}