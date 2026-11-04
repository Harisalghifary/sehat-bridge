# Quickstart

From a clean checkout to a running stack in about two minutes (after the Docker
images are built):

```bash
git clone git@github.com:Harisalghifary/sehat-bridge.git
cd sehat-bridge
cp .env.example .env
make up
make migrate
make seed
make demo
```

Open <http://localhost:8080>. The demo command prints one `[ok]` line per
product claim and exits non-zero on the first failure.

| Account | Tenant | Role |
|---|---|---|
| `owner-acme@example.com` / `demo-password-123` | `acme` | owner |
| `same@person.dev` / `demo-password-123` | `acme` / `globex` | admin / member |
| `ops@sehatbridge.dev` / `demo-password-123` | platform | operator |

The public site has seven pages: `/`, `/solusi`, `/integrasi`, `/demo`,
`/tentang`, `/faq`, and `/privasi`. The demo form writes to the backend lead
table with honeypot, timing, and rate-limit checks.

## What each service is

| URL | Service |
|---|---|
| <http://localhost:8080> | Next.js through Caddy (the only app URL) |
| <http://localhost:8080/masuk> | faskes app |
| <http://localhost:8080/ops/masuk> | operator console |
| <http://localhost:8080/api/docs> | FastAPI Swagger UI |
| <http://localhost:8080/api/v1/health/ready> | dependency readiness |
| <http://localhost:8080/api/v1/metrics> | Prometheus metrics |
| <http://localhost:9001> | MinIO console (`sehat` / `sehat-secret`) |
| <http://localhost:8025> | Mailpit (verification and reset email) |
| <http://localhost:8090/health> | mock SATUSEHAT |

## Common commands

```bash
make test               # unit + lint + typecheck
make test-integration   # real Postgres, Redis, MinIO, mock SATUSEHAT
make smoke              # bootstrap acceptance checks
make demo               # end-to-end claims with pass/fail lines
make worker             # SATUSEHAT outbox worker
make retention          # audit/lead retention
make restore-drill TENANT=acme
make rewrap-secrets OLD_KEY='previous-passphrase'
make screenshots        # regenerate docs/screenshots (Playwright)
```

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| build dies with `rpc error ... EOF` | Docker VM out of memory during parallel builds | `make build` (sequential); give Docker Desktop more RAM |
| `/` returns 502 | frontend still building | `docker compose logs -f frontend` |
| readiness shows `minio: error` | minio not up yet | wait, then `make health` |
| upload fails with a network error | bucket CORS missing | `docker compose logs minio-init` |
| `pnpm: command not found` | local checks only | `corepack enable` or install pnpm 10 |
| no reset email | Mailpit not running | `docker compose up -d mailpit`; open port 8025 |
| port already in use | another stack | change the host port in `docker-compose.yml` |

## Without Docker (app + API only)

```bash
# terminal 1
cd backend && uv sync && uv run uvicorn app.main:app --reload

# terminal 2
cd frontend && pnpm install && API_BASE_URL=http://localhost:8000 pnpm dev
```

Postgres, Redis, MinIO, Mailpit, and the mock SATUSEHAT still need to run
somewhere; Compose is the supported path for v0.1.0.