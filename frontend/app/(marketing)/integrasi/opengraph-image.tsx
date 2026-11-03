import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Status integrasi Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Status integrasi apa adanya.",
    "SATUSEHAT mode uji. BPJS dan LIS/RIS direncanakan.",
  );
}