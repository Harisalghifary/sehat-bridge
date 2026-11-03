import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Tentang Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Dibangun dengan jarak yang jujur dari klaim besar.",
    "Proyek independen untuk administrasi faskes Indonesia.",
  );
}