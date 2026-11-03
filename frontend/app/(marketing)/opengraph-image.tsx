import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Sehat Bridge — platform berkas dan integrasi faskes";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Satu alur untuk berkas, anggota, dan integrasi faskes.",
    "Mode uji, isolasi data per faskes, tanpa data pasien.",
  );
}