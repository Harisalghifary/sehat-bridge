#!/usr/bin/env bash
# M0 acceptance checks. Fails on the first broken claim.
set -euo pipefail

BASE="${BASE_URL:-http://localhost:8080}"
pass() { printf '[ok] %s\n' "$1"; }
fail() { printf '[fail] %s\n' "$1"; exit 1; }

command -v curl >/dev/null || fail "curl is required"

status=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/")
[ "$status" = "200" ] || fail "marketing page returned $status"
pass "frontend serves / through Caddy"

curl -fsS "$BASE/api/v1/health/ready" -o /tmp/sb-ready.json || fail "readiness endpoint unavailable"
python3 - <<'PY' || fail "a dependency is not ready"
import json, sys
data = json.load(open("/tmp/sb-ready.json"))
bad = {k: v for k, v in data["checks"].items() if v != "ok"}
if bad:
    print(bad, file=sys.stderr)
    sys.exit(1)
PY
pass "readiness: postgres, redis, minio"

status=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/docs")
[ "$status" = "200" ] || fail "API docs returned $status"
pass "API docs through Caddy"

headers=$(curl -s -D - -o /dev/null "$BASE/api/ping")
grep -qi '^set-cookie: sb_boot=1' <<<"$headers" || fail "frontend did not set its cookie"
grep -qi 'set-cookie:.*httponly' <<<"$headers" || fail "cookie is not HttpOnly"
pass "first-party cookie set by the frontend through Caddy"

status=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/health/live")
[ "$status" = "200" ] || fail "API liveness returned $status"
pass "API liveness"

printf '\nM0 smoke: all checks passed\n'