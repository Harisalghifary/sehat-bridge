import { ImageResponse } from "next/og";

export const ogSize = { width: 1200, height: 630 };
export const ogContentType = "image/png";

export function renderOgImage(title: string, subtitle: string) {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#ffffff",
          padding: "72px",
          fontFamily: "sans-serif",
          color: "#0b1f2a",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 12,
              background: "#0e7c7b",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 24,
              fontWeight: 700,
            }}
          >
            SB
          </div>
          <div style={{ fontSize: 30, fontWeight: 600 }}>Sehat Bridge</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div
            style={{
              fontSize: 68,
              lineHeight: 1.08,
              letterSpacing: "-0.02em",
              fontWeight: 600,
              maxWidth: 960,
            }}
          >
            {title}
          </div>
          <div
            style={{
              fontSize: 28,
              lineHeight: 1.4,
              color: "#3e5663",
              maxWidth: 900,
            }}
          >
            {subtitle}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            borderTop: "2px solid #e3eaee",
            paddingTop: 24,
            fontSize: 22,
            color: "#6b7c88",
          }}
        >
          <span>Platform faskes Indonesia · mode uji</span>
          <span>Proyek independen, bukan Kemenkes</span>
        </div>
      </div>
    ),
    ogSize,
  );
}