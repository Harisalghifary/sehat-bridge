# Sehat Bridge — Project Spec

Status: **v0.1.0 released (M0–M10 complete)**
Source design: `~/Haris/Seha Backend - System Design Document.pdf`
Target repo: `~/github/sehat-bridge` (monorepo: `backend/` JSON API, `frontend/` Next.js app)

## What this is

A multi-tenant platform and web product for Indonesian health facilities
(**faskes**), built on FastAPI + PostgreSQL + Redis + MinIO, with a Next.js 15
frontend (marketing site + faskes app + ops). Tenants are clinics, practices, or
labs. The platform stores their data in isolated schemas and is designed to
publish resources to **SATUSEHAT** (Kemenkes) through a swappable adapter.

v0.1.0 ships the platform, a public marketing site, the faskes app, and a
**mock-backed** SATUSEHAT integration. It does **not** depend on Kemenkes API
credentials, which require a registered PT/faskes and an onboarding agreement.

## Documents

| File | Contents |
|---|---|
| `00-handoff.md` | Session compact: decisions, state, next action |
| `01-product.md` | Naming, disclaimer, personas, scope, non-goals, glossary |
| `02-architecture.md` | Components, request lifecycle, tenancy, storage, integration adapter |
| `03-data-model.md` | Tables, indexes, RLS, migrations, integration tables |
| `04-api-spec.md` | REST endpoints, payloads, status codes, error envelope |
| `05-milestones.md` | M0–M10 with tasks, acceptance criteria, demos |
| `06-testing-ops.md` | Test matrix, CI, observability, runbook, risks |
| `07-adrs.md` | Architecture decision records |
| `08-ui.md` | Marketing pages, faskes app, ops, design system |
| `09-readme-and-demo.md` | README structure, screenshot harness, demo script |
| `quickstart.md` | clone-to-running commands and common failures |
| `api.md` | endpoint reference generated from OpenAPI |
| `satusehat.md` | mock boundaries and what going live requires |
| `runbook.md` | incident response, rotation, restore, stuck jobs |
| `design-review.md` | source-document flaws mapped to fixes or deferrals |
| `release.md` | v0.1.0 tag checklist |

## Reading order for a new dev

1. `01-product.md` — what we are and are not building, and the naming caveat
2. `02-architecture.md` — request lifecycle, tenancy invariant, adapter boundary
3. `05-milestones.md` — what to build first
4. `03`/`04`/`08` as reference while coding

## The two invariants

> **Tenancy:** a request may only ever see rows from the single tenant named in
> its verified JWT claim. Any path that reads tenant data outside
> `get_tenant_session()` is a bug.

> **Integration:** no module may call SATUSEHAT directly. All access goes through
> `modules/integrations/satusehat/port.py`, so `mock` and `live` are
> interchangeable by configuration.

## Conventions

- **MUST / MUST NOT** — enforced by tests, blocks merge.
- Estimates are focused-engineering days, not calendar days.
- Every milestone ends with a demo command a non-author can run.