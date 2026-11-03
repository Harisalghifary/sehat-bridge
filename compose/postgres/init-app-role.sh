#!/bin/sh
# Create the non-owner application role at cluster init time.
# Runs only on a fresh volume; tests and existing volumes create it explicitly.
set -eu

APP_DB_ROLE="${APP_DB_ROLE:-sehat_app}"
APP_DB_PASSWORD="${APP_DB_PASSWORD:-sehat_app}"

if ! psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$APP_DB_ROLE'" \
    --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" | grep -q 1; then
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    -c "CREATE ROLE \"$APP_DB_ROLE\" LOGIN PASSWORD '$APP_DB_PASSWORD'"
fi

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "GRANT CONNECT ON DATABASE \"$POSTGRES_DB\" TO \"$APP_DB_ROLE\""
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -c "GRANT USAGE ON SCHEMA public TO \"$APP_DB_ROLE\""