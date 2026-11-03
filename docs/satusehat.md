# SATUSEHAT integration

Sehat Bridge talks to SATUSEHAT through one interface, `SatusehatPort`
(`backend/app/integrations/satusehat/port.py`). Nothing outside that package
imports a FHIR client.

## Modes

| Mode | Selected by | Used for |
|---|---|---|
| `mock` (default) | `SATUSEHAT_MODE=mock` | local development, CI, the whole M5 pipeline |
| `live` | `SATUSEHAT_MODE=live` | a real Kemenkes sandbox/production deployment |

The adapter is chosen in `factory.py`; tenant credentials store the base URL
recorded when they were saved. The worker runs in Compose so it can resolve the
same internal hostnames as the API (`make worker`).

## Credentials

- Stored in the tenant schema (`integration_credentials`).
- `client_secret` is encrypted with Fernet. The key is derived from
  `APP_ENCRYPTION_KEY`, which is never stored in the database.
- The API returns only `has_secret: true`; the secret is never logged and never
  placed in audit metadata.
- Any credential change resets the status to `unverified`. A sync requires a
  successful `POST /integrations/satusehat/test` first.

## Outbox

```
sync request -> sync_jobs(queued) -> worker -> SatusehatPort
                                    |- success: sync_resources(local -> fhir) + done
                                    |- 5xx/timeout: backoff, max 5 -> dead
                                    `- 4xx: failed immediately
```

Properties implemented:

- **Transactional enqueue** — the job and its payload snapshot commit with the
  request.
- **Idempotency** — an existing `sync_resources` mapping short-circuits a new
  enqueue and the worker; the same sync returns the existing job.
- **Fairness** — one job per tenant per cycle, rotating start point.
- **Bounded retries** — exponential backoff (`2, 4, 8, 16…` seconds), then
  `dead`. Terminal 4xx goes straight to `failed`.
- **Resumability** — `running` jobs older than `WORKER_STALE_SECONDS` are
  requeued at worker startup/pass, so a killed worker does not strand work.
- **Redaction** — stored `response_body` has identifiers, names, and addresses
  replaced with `[redacted]`.

## Failure injection

The mock is query-driven, so no code changes are needed:

```bash
# retryable server error
.../fhir-r4/v1?fail=500
# terminal validation error
.../fhir-r4/v1?fail=4xx
# slow response, adapter timeout
.../fhir-r4/v1?fail=timeout
```

Tests set a tenant's stored `base_url` to one of these variants. The OAuth token
call deliberately drops the query, so token issuance still works and the failure
lands on the FHIR call.

## What the mock proves

- The pipeline, tenancy, encryption, outbox, retries, idempotency, and API shape.
- Deterministic FHIR ids (`sha256(type|identifier)[:24]`), so re-sync is stable.
- OAuth2 client-credentials flow shape and Bearer-protected FHIR calls.

## What it does not prove

- Kemenkes-specific profile/terminology validation, rate limits, and error
  payloads.
- Real organization registration and identifier rules.
- Production network, TLS, or credentials.

A live smoke test is intentionally opt-in; the default test suite never calls
Kemenkes.

## Demo

```bash
make up
make seed
make integration-demo
```

The demo stores mock credentials for `acme`, tests the connection, enqueues an
organization sync, runs one worker pass in Compose, and prints the job plus the
per-resource `fhir_id` mapping.