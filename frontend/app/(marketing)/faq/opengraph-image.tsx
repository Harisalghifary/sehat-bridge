import { ogContentType, ogSize, renderOgImage } from "@/lib/og";

export const alt = "FAQ Sehat Bridge";
export const size = ogSize;
export const contentType = ogContentType;

export default function Image() {
  return renderOgImage(
    "Pertanyaan yang sering muncul.",
    "Jawaban jujur soal SATUSEHAT mode uji, data, dan keamanan.",
  );
}