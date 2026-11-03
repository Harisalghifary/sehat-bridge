import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Solusi Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Empat bagian, satu model data.",
    "Berkas, anggota, integrasi, dan audit untuk faskes.",
  );
}