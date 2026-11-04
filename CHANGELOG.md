# Changelog

All notable changes to this project are documented here.

## v0.1.0 — 2026-11-05

### Added

- Multi-tenant FastAPI backend with schema-per-tenant isolation, RLS, and
  `SET LOCAL` tenant context.
- Authentication with argon2id, rotating opaque refresh tokens, platform-scoped
  operator tokens, and Redis-backed session BFF.
- Tenant faskes app: dashboard, presigned file uploads, members and roles,
  SATUSEHAT mock integration, profile, settings.
- Ops console: tenant provisioning, suspend/resume, audit log, dependency and
  queue health.
- Marketing site with demo lead capture and original Indonesian copy.
- M9 hardening: idempotency replay, structured request logs with request ids,
  Prometheus metrics, optional OTLP tracing, retention jobs, email verification
  and password reset through Mailpit, OpenAPI contract tests.
- Operator runbook, restore drill, encryption-key rotation, and demo script.
- M10 documentation, screenshot harness, and release checklist.

### Known limits

- SATUSEHAT runs against a local mock; real production traffic is not proven.
- No clinical data, patient records, or NIK storage.
- Compose is the supported deployment for v0.1.0.