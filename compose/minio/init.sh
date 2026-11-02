#!/bin/sh
set -eu

echo "waiting for minio..."
until mc alias set local "http://minio:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 1
done

mc mb --ignore-existing "local/$MINIO_BUCKET"
mc anonymous set none "local/$MINIO_BUCKET"
mc cors set "local/$MINIO_BUCKET" /config/cors.xml

echo "minio ready: bucket=$MINIO_BUCKET cors=applied"