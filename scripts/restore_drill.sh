#!/usr/bin/env bash
# Restore one tenant schema into a scratch schema and prove the column shape
# matches. Run against a live Compose stack: make restore-drill TENANT=acme
set -euo pipefail

TENANT="${1:-}"
if [[ -z "$TENANT" ]]; then
  echo "usage: $0 <tenant-slug>" >&2
  exit 2
fi
if [[ ! "$TENANT" =~ ^[a-z0-9][a-z0-9_-]{1,62}$ ]]; then
  echo "invalid tenant slug: $TENANT" >&2
  exit 2
fi

SCHEMA="tenant_${TENANT//-/_}"
SCRATCH="${SCHEMA}_restore"
DUMP="$(mktemp -t sehat-bridge-restore.XXXXXX.sql)"
COLS_ORIG="$(mktemp -t sehat-bridge-columns-orig.XXXXXX)"
COLS_REST="$(mktemp -t sehat-bridge-columns-rest.XXXXXX)"
trap 'rm -f "$DUMP" "$COLS_ORIG" "$COLS_REST"' EXIT

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

pg() {
  compose exec -T postgres "$@"
}

echo "[..] dumping $SCHEMA"
pg pg_dump -U sehat -d sehat --schema="$SCHEMA" --schema-only --no-owner --no-privileges > "$DUMP"

echo "[..] restoring into $SCRATCH"
sed "s/${SCHEMA}/${SCRATCH}/g" "$DUMP" | pg psql -q -U sehat -d sehat -v ON_ERROR_STOP=1 >/dev/null

echo "[..] comparing column shapes"
columns() {
  pg psql -At -U sehat -d sehat -c "
    SELECT table_name || '.' || column_name || ':' || data_type || ':' || is_nullable
      FROM information_schema.columns
     WHERE table_schema = '$1'
     ORDER BY table_name, ordinal_position"
}

columns "$SCHEMA" > "$COLS_ORIG"
columns "$SCRATCH" | sed "s/${SCRATCH}/${SCHEMA}/g" > "$COLS_REST"
if ! diff -u "$COLS_ORIG" "$COLS_REST"; then
  pg psql -q -U sehat -d sehat -c "DROP SCHEMA IF EXISTS \"$SCRATCH\" CASCADE" >/dev/null
  echo "[fail] restored schema does not match $SCHEMA" >&2
  exit 1
fi

pg psql -q -U sehat -d sehat -c "DROP SCHEMA IF EXISTS \"$SCRATCH\" CASCADE" >/dev/null
echo "[ok] restore drill: $SCHEMA restored and matched column-for-column"