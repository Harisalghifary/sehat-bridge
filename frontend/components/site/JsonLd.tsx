export function JsonLd({ data }: { data: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      // JSON.stringify escapes the content; no user input is interpolated.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}