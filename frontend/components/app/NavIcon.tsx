const paths: Record<string, string> = {
  dashboard: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z",
  files: "M4 4h6l2 2h8v14H4zM8 12h8M8 16h5",
  members: "M9 11a4 4 0 100-8 4 4 0 000 8zM2 21a7 7 0 0114 0M17 11a3 3 0 100-6M18 21a5 5 0 013-4.6",
  integration: "M8 12H3M21 12h-5M8 7H6a5 5 0 000 10h2M16 7h2a5 5 0 010 10h-2M12 4v16",
  profile: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0",
  tenants:
    "M4 21V8l8-4 8 4v13M9 21v-6h6v6M8 10h.01M12 10h.01M16 10h.01",
  audit: "M8 4h9l3 3v13H8zM17 4v4h4M11 12h6M11 16h6",
  health: "M3 12h4l2-6 4 12 2-6h6",
  settings:
    "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12a7 7 0 00-.1-1l2-1.5-2-3.4-2.3 1a7 7 0 00-1.7-1L14.5 3h-5l-.4 2.6a7 7 0 00-1.7 1l-2.3-1-2 3.4L5.1 11a7 7 0 000 2l-2 1.5 2 3.4 2.3-1a7 7 0 001.7 1l.4 2.6h5l.4-2.6a7 7 0 001.7-1l2.3 1 2-3.4-2-1.5a7 7 0 00.1-1z",
};

export function NavIcon({ name }: { name: string }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="size-5 shrink-0"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[name] ?? paths.dashboard} />
    </svg>
  );
}