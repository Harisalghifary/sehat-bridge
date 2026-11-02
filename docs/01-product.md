# 01 — Product, Scope & Naming

## 1. Naming

**Chosen: `sehat-bridge`.** Product name: **Sehat Bridge**.

Rationale:
- "sehat" is the Indonesian word the source document's name derives from, and it
  reads naturally to the target market.
- "bridge" states the job: connecting faskes systems to SATUSEHAT, not replacing
  either side.
- It avoids claiming the program's name.

### Naming caveat (read before branding)

**SATUSEHAT / Satu Sehat is an official Kemenkes program.** This project is
**not affiliated with, endorsed by, or operated by Kemenkes.** Rules:

- MUST NOT use the SATUSEHAT logo or wordmark, or any Kemenkes visual identity.
- MUST NOT present the product as "official", "resmi", or "terintegrasi resmi"
  until a real partnership exists.
- MUST include a disclaimer in `README.md` and the site footer:
  *"Sehat Bridge is an independent project and is not affiliated with Kemenkes."*
- Descriptive references ("integrates with SATUSEHAT") are fine; use of the name
  as *our* brand is not.

Rejected alternatives: `satusehat-bridge` (strongest affiliation signal, fine
only for a private demo), `rekam-sehat` (RME is a regulated term), `nusa-sehat`
(brandable but vague), `seha-platform` (keeps the PDF's ambiguous name).

## 2. What Sehat Bridge is, for the MVP

A **multi-tenant health platform backend + web product** for small Indonesian
health facilities.

- A **tenant** is one faskes (klinik, praktik mandiri, lab).

**Locked decision:** one tenant = one faskes. A PT that owns several facilities is
modelled as several tenants sharing an owner identity (same email, multiple
memberships) — not as a parent tenant with children. There is no facility
hierarchy in v0.1.0, which keeps the schema flat and the RLS policy simple. If a
group-level rollup is ever needed, it becomes a reporting view across tenants, not
a tenancy level.
- Each tenant has isolated data, its own members and roles, and its own
  integration credentials.
- The platform can push selected records to SATUSEHAT via a FHIR R4 adapter.
- SATUSEHAT access requires a legal entity (PT) and faskes onboarding, so v0.1.0
  runs the adapter against a **deterministic mock** that speaks the same FHIR
  shapes. Nothing in the product is blocked on Kemenkes approval.

## 3. Personas

| Persona | Needs | MVP surface |
|---|---|---|
| **Prospective customer** (hospital/clinic manager) | Understand the product, trust it, book a demo | Marketing site + demo form |
| **Faskes owner** | Manage staff and roles, see storage usage, connect SATUSEHAT | App: dasbor, anggota, integrasi |
| **Faskes admin** | Upload/manage documents, run a sync | App: berkas, integrasi |
| **Faskes staff** | Log in, edit profile, access shared documents | App: profil, berkas |
| **Platform operator** | Provision tenants, suspend abuse, watch health, audit actions | `/ops` |
| **Integrator** | A stable, documented API | OpenAPI + error contract |

## 4. In scope (v0.1.0)

**Platform**
- Tenant provisioning from the CLI and the ops area, idempotent and audited
- Schema-per-tenant isolation: transaction-scoped `search_path` + RLS backup
- Email/password auth, argon2id, short access token, rotating refresh token
- Roles `owner` / `admin` / `member`, enforced server-side
- Tenant-scoped files via presigned MinIO uploads with size/MIME/quota limits
- Audit log, idempotency keys, cursor pagination, one error envelope
- Structured logs, request IDs, metrics, liveness/readiness

**Web product (Next.js, single app)**
- Public marketing site: beranda, solusi, integrasi, demo, tentang, FAQ, privasi
- Auth pages: masuk, daftar, lupa sandi
- Faskes app: dasbor, berkas, integrasi, anggota, profil
- Ops area: tenant, audit, kesehatan sistem
- SSR/SSG with SEO metadata, sitemap, OG images; Lighthouse ≥ 90
- Cookie session via a server-side BFF; tokens never reach the browser
- Bahasa Indonesia only; structure ready for `en` later

**SATUSEHAT integration (mock)**
- Port/adapter boundary with `mock` and `live` implementations
- Per-tenant encrypted credentials, OAuth2 client-credentials against the mock
- Push of `Organization` and `Patient` (minimal FHIR R4) with idempotent retry
- Sync job history and per-resource status visible in the app

## 5. Out of scope (v0.1.0) — and why

| Deferred | Reason |
|---|---|
| Real SATUSEHAT production traffic | Requires PT + faskes onboarding + Kemenkes agreement |
| Patient-facing app / booking | Different product, different compliance surface |
| Full EMR (encounters, observations, prescriptions) | Needs clinical domain decisions; mock already proves the pipeline |
| Storing NIK / patient PII at rest | UU PDP obligations; not needed to prove the adapter |
| OAuth/SSO, MFA | Enterprise features without a customer yet |
| Billing, WhatsApp/email notifications | Undefined commercial model |
| WebSockets / realtime | No consumer; polling covers sync status |
| Sharding, multi-region, K8s | Tenant count is tens |
| Blog/CMS, case studies, careers page | Content pipeline without a content owner |
| Clinical screens in the app (patients, encounters) | Requires a clinical data model; deferred by decision |
| Patient-facing booking/chat | Different product and compliance surface |

## 6. Success criteria for v0.1.0

1. Fresh clone → working demo in one documented command.
2. Two tenants coexist with zero data bleed, proven under a two-connection pool
   with interleaved requests; a forged `X-Tenant-ID` returns 403.
3. A faskes admin can complete the app journey: log in → upload a document →
   connect the integration → run a sync → see per-resource results.
4. The public site renders every page with real copy, passes Lighthouse ≥ 90 on
   mobile for performance and accessibility, and its demo form writes a lead.
5. Switching `SATUSEHAT_MODE=mock` to `live` changes **only** configuration; a
   contract test proves the adapter calls the same port methods.
6. Full suite green in CI under 8 minutes.
7. An integrator can answer every question from the OpenAPI docs alone.
8. Tenant #3 provisioned in under 30 seconds from `/ops`.

## 7. Glossary

| Term | Meaning |
|---|---|
| **Faskes** | *Fasilitas kesehatan* — a health facility; one tenant |
| **SATUSEHAT** | Kemenkes national health data platform (FHIR R4 based) |
| **Tenant** | An organisation; one PostgreSQL schema `tenant_<slug>` |
| **Membership** | Link between a global user and a tenant, carrying a role |
| **Slug** | URL-safe tenant id, `^[a-z0-9][a-z0-9_-]{1,62}$` |
| **Tenant schema** | `tenant_<slug>`; holds all tenant-owned tables |
| **Platform operator** | Operator with no tenant membership; provisions tenants |
| **Access token** | Short-lived JWT (15 min): `sub`, `tid`, `role`, `jti` |
| **Refresh token** | Opaque 256-bit secret, hashed at rest, rotating, revocable |
| **Adapter** | `mock` or `live` implementation behind `SatusehatPort` |
| **Outbox** | `sync_jobs` rows that guarantee a push is retried until terminal |