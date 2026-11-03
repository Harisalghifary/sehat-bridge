# Quickstart

```bash
git clone git@github.com:Harisalghifary/sehat-bridge.git
cd sehat-bridge
cp .env.example .env
make up
make smoke
make migrate
make seed
```

Open <http://localhost:8080>.

The public site has seven pages: `/`, `/solusi`, `/integrasi`, `/demo`,
`/tentang`, `/faq`, and `/privasi`. The demo form writes to the backend lead
table (with honeypot, timing, and rate-limit checks) and is rate limited per IP.

Postgres is published on host port **55432** (5432 is commonly occupied by a
local install). The container still listens on 5432 internally.

## What each service is

| URL | Service |
|---|---|
| <http://localhost:8080> | Next.js through Caddy (the only app URL) |
| <http://localhost:8080/api/docs> | FastAPI Swagger UI |
| <http://localhost:8080/api/v1/health/ready> | dependency readiness |
| <http://localhost:9001> | MinIO console (`sehat` / `sehat-secret`) |
| <http://localhost:8025> | Mailpit |
| <http://localhost:8090/health> | mock SATUSEHAT |

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| build dies with `rpc error ... EOF` | Docker VM out of memory during parallel builds | `make build` (sequential); give Docker Desktop more RAM |
| `/` returns 502 | frontend still building | `docker compose logs -f frontend` |
| readiness shows `minio: error` | minio not up yet | wait, then `make health` |
| upload fails with a network error | bucket CORS missing | `docker compose logs minio-init` |
| `pnpm: command not found` | local checks only | `corepack enable` or install pnpm 10 |
| port already in use | another stack | change the host port in `docker-compose.yml` |

## Without Docker (app + API only)

```bash
# terminal 1
cd backend && uv sync && uv run uvicorn app.main:app --reload

# terminal 2
cd frontend && pnpm install && API_BASE_URL=http://localhost:8000 pnpm dev
```

Postgres, Redis, and MinIO still need to run somewhere; Compose is the supported
path for v0.1.0.