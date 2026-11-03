import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "Jadwalkan demo Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Lihat alurnya dengan data contoh.",
    "Demo 30 menit: berkas, peran, dan antrean SATUSEHAT mode uji.",
  );
}