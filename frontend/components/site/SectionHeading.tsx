export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--brand)]">
      {children}
    </p>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = "left",
  id,
  as: Heading = "h2",
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
  id?: string;
  as?: "h1" | "h2";
}) {
  return (
    <div
      className={`max-w-3xl ${align === "center" ? "mx-auto text-center" : ""}`}
    >
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Heading id={id} className="h2 mt-3">
        {title}
      </Heading>
      {description ? <p className="lead mt-4">{description}</p> : null}
    </div>
  );
}