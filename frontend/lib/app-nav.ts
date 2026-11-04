export type AppRole = "owner" | "admin" | "member";

export const appNav = [
  {
    href: "/app/dasbor",
    label: "Dasbor",
    icon: "dashboard" as const,
    roles: ["owner", "admin", "member"] as AppRole[],
  },
  {
    href: "/app/berkas",
    label: "Berkas",
    icon: "files" as const,
    roles: ["owner", "admin", "member"] as AppRole[],
  },
  {
    href: "/app/anggota",
    label: "Anggota",
    icon: "members" as const,
    roles: ["owner", "admin"] as AppRole[],
  },
  {
    href: "/app/integrasi",
    label: "Integrasi",
    icon: "integration" as const,
    roles: ["owner", "admin"] as AppRole[],
  },
  {
    href: "/app/profil",
    label: "Profil",
    icon: "profile" as const,
    roles: ["owner", "admin", "member"] as AppRole[],
  },
  {
    href: "/app/pengaturan",
    label: "Pengaturan",
    icon: "settings" as const,
    roles: ["owner", "admin", "member"] as AppRole[],
  },
];

export const breadcrumbLabels: Record<string, string> = {
  app: "Aplikasi",
  dasbor: "Dasbor",
  berkas: "Berkas",
  anggota: "Anggota",
  integrasi: "Integrasi",
  profil: "Profil",
  pengaturan: "Pengaturan",
};