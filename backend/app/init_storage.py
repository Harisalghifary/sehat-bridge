"""Create the object-storage bucket and apply its CORS policy.

Runs as a one-shot Compose job (``python -m app.init_storage``) because MinIO
stopped publishing the ``mc`` client image. Using the S3 API keeps the bootstrap
portable across MinIO, Garage, or any S3-compatible provider.

Idempotent: safe to re-run on every ``docker compose up``.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2.0


def cors_rules(origin: str) -> dict[str, list[dict[str, Any]]]:
    """CORS policy for direct browser uploads via presigned POST."""
    return {
        "CORSRules": [
            {
                "AllowedOrigins": [origin],
                "AllowedMethods": ["GET", "HEAD", "POST", "PUT"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000,
            }
        ]
    }


def build_client() -> Any:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_root_user,
        aws_secret_access_key=settings.minio_root_password,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 1},
        ),
    )


def wait_for_storage(client: Any) -> bool:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            client.list_buckets()
        except (BotoCoreError, ClientError):
            if attempt == MAX_ATTEMPTS:
                return False
            time.sleep(DELAY_SECONDS)
        else:
            return True
    return False


def main() -> int:
    settings = get_settings()
    client = build_client()

    if not wait_for_storage(client):
        print("storage init: object storage unreachable", file=sys.stderr)
        return 1

    try:
        client.create_bucket(Bucket=settings.minio_bucket)
        print(f"storage init: created bucket {settings.minio_bucket}")
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise
        print(f"storage init: bucket {settings.minio_bucket} already present")

    client.put_bucket_cors(
        Bucket=settings.minio_bucket,
        CORSConfiguration=cors_rules(settings.site_url),
    )
    print(f"storage init: cors allows {settings.site_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
