import type { MetadataRoute } from "next";

import { site } from "@/lib/site";

const base = site.url.replace(/\/$/, "");

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date("2026-11-04");
  return [
    { url: `${base}/`, lastModified, changeFrequency: "weekly", priority: 1 },
    {
      url: `${base}/solusi`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${base}/integrasi`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.8,
    },
    {
      url: `${base}/demo`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.9,
    },
    {
      url: `${base}/tentang`,
      lastModified,
      changeFrequency: "yearly",
      priority: 0.6,
    },
    {
      url: `${base}/faq`,
      lastModified,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${base}/privasi`,
      lastModified,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];
}