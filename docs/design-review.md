# Design review — source documents vs. what shipped

The source set was a broad product brief plus a dhealth.co.id structural
reference. This review records every material flaw, how v0.1.0 addresses it, or
why it is deliberately deferred. A deferred item is not silently dropped; it has
a trigger in `docs/00-handoff.md` or an ADR.

## 1. Product and positioning

| Source flaw | Fix in v0.1.0 | Status |
|---|---|---|
| Implied Kemenkes affiliation | Independent-project disclaimer above the first screenshot, in the footer, and in `/tentang` | Fixed |
| Real customer logos/testimonials used as social proof | All names are fictional and labelled, or removed; no copied logos or quotes | Fixed |
| Unverifiable statistics (“40% faster”, “500 faskes”) | No claim without a source; illustrative numbers are labelled | Fixed |
| Scope drift into clinical records (patients, encounters, NIK) | Clinical data is explicitly out of scope; new milestone + ADR required | Deferred by design |
| “One platform for everything” positioning | Narrow promise: files, members, roles, mock SATUSEHAT in one flow | Fixed |
| No statement of who this is for | Personas and success criteria in `01-product.md`; copy speaks to clinic managers | Fixed |

## 2. Architecture and security

| Source flaw | Fix in v0.1.0 | Status |
|---|---|---|
| Tenant from `X-Tenant-ID` alone | JWT `tid` is authoritative; header hints must match or `403 tenant_mismatch` | Fixed |
| Single shared schema with app-level filters | Schema-per-tenant + `SET LOCAL search_path` + FORCE RLS as second layer | Fixed |
| Tokens in browser storage | Next.js BFF stores tokens in Redis; `__Host` cookies only reach the server | Fixed |
| bcrypt default | argon2id with uniform failure timing and a dummy verify | Fixed |
| Refresh tokens as long-lived JWTs | Opaque, hashed at rest, rotating, family reuse detection | Fixed |
| HTMX ops console | Superseded by ADR-016; one Next.js app covers marketing, app, ops | Fixed |
| Realtime/WebSockets assumed | Removed from scope; no websocket dependency in the build | Fixed |
| Mock integration presented as production-ready | `Mode uji` band, mock-only docs, and “unproven” section in `satusehat.md` | Fixed |
| No idempotency for retried mutations | Redis `Idempotency-Key` replay for 24 hours, mismatch → `422` | Fixed (M9) |
| Secret rotation hand-waved | `make rewrap-secrets` + runbook rotation drill | Fixed (M9) |
| Backup/restore as a someday task | `make restore-drill` proves a tenant schema restore column-for-column | Fixed (M9) |

## 3. UI and accessibility

| Source flaw | Fix in v0.1.0 | Status |
|---|---|---|
| Mobile treated as a smaller desktop | 390px passes with card tables, 44px touch targets, drawer focus trap | Fixed |
| Animations without a reduced-motion path | `prefers-reduced-motion` disables motion globally | Fixed |
| Colour-only status | Status text + dot, table headers with `scope`, visible focus | Fixed |
| Charts and numbers without provenance | No fabricated dashboard numbers; every value traces to an API response | Fixed |
| Ops exposed in the faskes nav to everyone | Role-filtered nav; tenant users are sent to operator login; API enforces 403 | Fixed |
| Password reset promised but absent | Email verification + reset via Mailpit, single-use tokens | Fixed (M9) |
| “Export CSV” and “suspend reason” invented in the UI spec | Removed from v0.1.0 scope; not claimed in the shipped UI | Deferred |
| Dark mode assumed | Not shipped; one light theme with semantic tokens | Deferred |
| Metric-heavy hero visuals | Literal product UI compositions, no glossy mockups | Fixed |

## 4. Operations

| Source flaw | Fix in v0.1.0 | Status |
|---|---|---|
| Run without SQL by memory | Ops console + `docs/runbook.md` + demo script | Fixed |
| No request correlation | One JSON log line per request, same `X-Request-ID` as the problem body | Fixed (M9) |
| Metrics named but not exposed | Prometheus endpoint with HTTP latency, auth, provisioning, files, pool | Fixed (M9) |
| Traces assumed without an exporter | OTel tracing is off by default and enabled by `OTEL_EXPORTER_OTLP_ENDPOINT` | Fixed (M9) |
| Retention unspecified | Audit/lead retention CLI, default 365 days | Fixed (M9) |
| Chaos behaviour asserted but untested | Redis/MinIO/mock failure expectations documented and exercised manually | Verified |
| Untested real Kemenkes traffic | Live adapter selected by config only; not presented as proven | Deferred |

## 5. Decisions that remain open

| Topic | Default | Trigger |
|---|---|---|
| Deploy target | Compose-only | First hosting decision |
| Custom domain | `NEXT_PUBLIC_SITE_URL` | Before public launch |
| WhatsApp/demo number | Placeholder in `.env` | Before campaign |
| Legal entity name | “Sehat Bridge (proyek independen)” | Before contracting |
| SSO/MFA | Not in v0.1.0 | First enterprise requirement |
| Real SATUSEHAT production | Mock only | PT + faskes onboarding + Kemenkes agreement |

## 6. Review method

Each item was checked against a test, a runbook step, or an explicit deferral.
The M10 gate requires this file to be updated whenever a source claim changes
status. Screenshots and README claims are reviewed against this table before a
release tag.