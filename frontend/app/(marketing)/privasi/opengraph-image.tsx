import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Kebijakan privasi Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Privasi dalam bahasa sehari-hari.",
    "Data lead, cookie sesi, masa simpan, dan cara meminta penghapusan.",
  );
}