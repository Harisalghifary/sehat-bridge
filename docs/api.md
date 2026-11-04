# API reference

Generated from the running FastAPI schema by `cd backend && uv run python scripts/generate_api_docs.py`.
Do not hand-edit. Swagger UI is at `/api/docs`.

Base path `/api/v1`. Errors use `application/problem+json` with `type`, `title`, `status`, `code`, `trace_id`, and `details`.
Send `Authorization: Bearer <access_token>` on every row marked private.
Send `Idempotency-Key` on mutating requests to make retries safe.

| Method | Path | Auth | Summary |
|---|---|---|---|
| GET | `/api/v1/admin/audit` | private | Query the audit log |
| GET | `/api/v1/admin/audit/actions` | private | Known audit actions |
| GET | `/api/v1/admin/health` | private | Operator health summary |
| GET | `/api/v1/admin/me` | private | Current operator |
| POST | `/api/v1/admin/migrations/tenants` | private | Apply pending tenant migrations |
| GET | `/api/v1/admin/tenants` | private | List tenants |
| POST | `/api/v1/admin/tenants` | private | Provision a tenant |
| GET | `/api/v1/admin/tenants/{slug}` | private | Tenant detail |
| POST | `/api/v1/admin/tenants/{slug}/resume` | private | Resume a tenant |
| POST | `/api/v1/admin/tenants/{slug}/suspend` | private | Suspend a tenant |
| POST | `/api/v1/auth/login` | public | Log in to a tenant |
| POST | `/api/v1/auth/logout` | private | Log out and optionally revoke the refresh family |
| POST | `/api/v1/auth/password-reset/confirm` | public | Set a new password using a reset token |
| POST | `/api/v1/auth/password-reset/request` | public | Request a password reset link |
| POST | `/api/v1/auth/platform-login` | public | Log in as a platform operator (no tenant) |
| POST | `/api/v1/auth/refresh` | public | Rotate a refresh token |
| POST | `/api/v1/auth/register` | public | Register into an existing tenant |
| POST | `/api/v1/auth/verify-email` | private | Send (or resend) an email verification link |
| POST | `/api/v1/auth/verify-email/confirm` | public | Confirm an email verification token |
| GET | `/api/v1/files` | private | List files, newest first |
| POST | `/api/v1/files/presign-upload` | private | Reserve quota and sign a direct upload |
| GET | `/api/v1/files/usage` | private | Tenant storage usage |
| DELETE | `/api/v1/files/{file_id}` | private | Soft-delete a file |
| POST | `/api/v1/files/{file_id}/complete` | private | Verify an uploaded object and mark it ready |
| GET | `/api/v1/files/{file_id}/download` | private | Issue a short-lived download URL |
| GET | `/api/v1/health/live` | public | Liveness probe |
| GET | `/api/v1/health/ready` | public | Readiness probe |
| GET | `/api/v1/integrations/satusehat` | private | Get SATUSEHAT configuration |
| PUT | `/api/v1/integrations/satusehat` | private | Store SATUSEHAT credentials |
| GET | `/api/v1/integrations/satusehat/jobs` | private | List sync jobs |
| GET | `/api/v1/integrations/satusehat/jobs/{job_id}` | private | Get a sync job |
| POST | `/api/v1/integrations/satusehat/sync` | private | Queue a resource sync |
| POST | `/api/v1/integrations/satusehat/test` | private | Test credentials against the configured adapter |
| POST | `/api/v1/leads` | public | Submit a demo request |
| GET | `/api/v1/metrics` | public | Prometheus metrics |
| GET | `/api/v1/public/health` | public | Public status |
| GET | `/api/v1/users` | private | List members of the current tenant |
| GET | `/api/v1/users/me` | private | Current user and membership |
| PATCH | `/api/v1/users/me` | private | Update your profile |
| PATCH | `/api/v1/users/{user_id}/role` | private | Change a member's role |
| GET | `/health/live` | private | Liveness probe |
| GET | `/health/ready` | private | Readiness probe |
| GET | `/public/health` | private | Public status |

## Error codes

See `docs/04-api-spec.md §6`. Every problem body includes the same `request_id` returned in the `X-Request-ID` response header.

## Generation

```bash
cd backend && uv run python scripts/generate_api_docs.py
```
