# Sehat Bridge

**Platform multi-tenant untuk fasilitas kesehatan Indonesia** — berkas, anggota,
peran, dan integrasi SATUSEHAT dalam satu alur.

> Sehat Bridge adalah proyek independen dan **tidak berafiliasi dengan Kemenkes**.
> Integrasi SATUSEHAT berjalan dalam mode uji dengan adapter mock. Tidak ada
> trafik produksi Kemenkes dan tidak ada data pasien yang disimpan.

[![CI](https://github.com/Harisalghifary/sehat-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/Harisalghifary/sehat-bridge/actions/workflows/ci.yml)

## Status

**M7 — aplikasi faskes.** The private app is live at `/masuk`: login through a
Redis-backed session BFF (tokens never reach the browser), dashboard, presigned
file upload with progress, members and roles, SATUSEHAT credentials/test/sync,
profile, and settings. The marketing site from M6 is unchanged. All app pages
read data from the API; nothing is hard-coded. Ops console and screenshots
follow in M8–M10 (see `docs/05-milestones.md`).

```bash
make migrate     # public schema
make seed        # two demo tenants + platform operator
```

| Akun | Tenant | Sandi |
|---|---|---|
| `owner-acme@example.com` | acme (owner) | `demo-password-123` |
| `same@person.dev` | acme (admin) / globex (member) | `demo-password-123` |
| `ops@sehatbridge.dev` | platform (no tenant) | `demo-password-123` |

```bash
make tenant NAME=klinik-sehat OWNER=owner-klinik@example.com TITLE="Klinik Sehat"
```

## Menjalankan

Prasyarat: Docker (dengan Compose), `uv`, Node 20, dan `pnpm`.

```bash
cp .env.example .env
make up          # build + start postgres, redis, minio, backend, frontend, caddy
make smoke       # M0 acceptance checks
make migrate     # public schema (Alembic)
make seed        # two demo tenants
make integration-demo  # credentials -> test -> sync -> worker result table
make worker      # outbox worker on the Compose network
make sweep       # release expired uploads
```

Buka <http://localhost:8080> untuk aplikasi, <http://localhost:8080/masuk>
untuk masuk ke aplikasi faskes, dan <http://localhost:8080/api/docs> untuk API.
MinIO console di <http://localhost:9001>, Mailpit di <http://localhost:8025>.

Pengembangan lokal tanpa Docker untuk aplikasi/API:

```bash
make install
make test        # pytest + eslint + tsc
make lint        # ruff + mypy + eslint + tsc
```

Hentikan stack dengan `make down` (volume tetap disimpan).

## Struktur

```
backend/         FastAPI 0.115 · Python 3.12 · SQLAlchemy async · uv
frontend/        Next.js 15 (App Router) · React 19 · Tailwind 4 · pnpm
tools/           mock-satusehat · screenshot harness
compose/         MinIO bucket + CORS init
docs/            spesifikasi produk, arsitektur, API, ADR, milestone
scripts/         smoke test
Caddyfile        satu origin: / → frontend, /api → backend
```

## Arsitektur singkat

- **Satu origin** lewat Caddy, jadi cookie sesi bersifat first-party dan tidak ada
  CORS antara aplikasi dan API.
- **Tenant = satu faskes.** Identitas tenant berasal dari klaim `tid` pada JWT,
  tidak pernah dari header yang bisa dipalsukan.
- **Schema per tenant** dengan `SET LOCAL search_path` dan RLS sebagai lapisan
  kedua.
- **Token tidak pernah mencapai browser.** Next.js menyimpan sesi di Redis dan
  memanggil API dari server.
- **SATUSEHAT** diakses lewat `SatusehatPort`; `mock` adalah default, `live` hanya
  berubah konfigurasi.

Detail: `docs/02-architecture.md` dan `docs/07-adrs.md`.

## API

| Method | Path | Keterangan |
|---|---|---|
| GET | `/api/v1/health/live` | liveness |
| GET | `/api/v1/health/ready` | status postgres, redis, minio |
| GET | `/api/v1/public/health` | status ringkas untuk situs publik |
| POST | `/api/v1/leads` | formulir demo (rate limited, honeypot) |
| GET | `/api/docs` | Swagger UI (mode dev) |

Kontrak lengkap ada di `docs/04-api-spec.md`; sumber kebenaran adalah OpenAPI.

## Dokumentasi

| Dokumen | Isi |
|---|---|
| `docs/00-handoff.md` | ringkasan keputusan dan langkah berikutnya |
| `docs/01-product.md` | persona, ruang lingkup, kriteria sukses |
| `docs/02-architecture.md` | komponen, siklus request, sesi, port |
| `docs/03-data-model.md` | skema public/tenant, RLS, migrasi |
| `docs/04-api-spec.md` | endpoint, payload, status code |
| `docs/05-milestones.md` | M0–M10 dan acceptance criteria |
| `docs/06-testing-ops.md` | matriks tes, CI, runbook |
| `docs/07-adrs.md` | ADR-001…017 |
| `docs/08-ui.md` | situs, aplikasi, ops, design system |
| `docs/09-readme-and-demo.md` | screenshot dan demo |
| `docs/satusehat.md` | adapter, batas mock, dan yang belum terbukti |

## Lisensi

MIT — lihat `LICENSE`.