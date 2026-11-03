"""S3-compatible object storage helpers.

Two endpoints are deliberate: the backend talks to MinIO over the internal
Compose network, while presigned URLs must be signed for the host the browser
can reach. Signing with the internal host would produce URLs that fail DNS in
the browser even though the signature is valid.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import aioboto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings, get_settings
from app.errors import AppError

SIGNING_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    retries={"max_attempts": 1},
    request_checksum_calculation="when_required",
    response_checksum_validation="when_required",
)


def _storage_error(exc: Exception) -> AppError:
    return AppError(
        status=503,
        code="storage_unavailable",
        title="Object storage is unavailable",
        detail=str(exc) if not get_settings().is_prod else None,
    )


@asynccontextmanager
async def _client(settings: Settings, *, public: bool = False) -> AsyncIterator[Any]:
    endpoint = settings.minio_public_url if public else settings.minio_endpoint
    session = aioboto3.Session()
    try:
        async with session.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
            region_name="us-east-1",
            config=SIGNING_CONFIG,
        ) as client:
            yield client
    except (BotoCoreError, ClientError) as exc:
        raise _storage_error(exc) from exc


async def _call(result: Any) -> Any:
    """aioboto3 returns presign helpers synchronously, others as coroutines."""
    if inspect.isawaitable(result):
        return await result
    return result


async def presign_post(
    *,
    key: str,
    content_type: str,
    size_bytes: int,
    expires_in: int,
) -> dict[str, Any]:
    settings = get_settings()
    async with _client(settings, public=True) as client:
        post = await _call(
            client.generate_presigned_post(
                Bucket=settings.minio_bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", size_bytes, size_bytes],
                ],
                ExpiresIn=expires_in,
            )
        )
    return dict(post)


async def presign_get(*, key: str, expires_in: int) -> str:
    settings = get_settings()
    async with _client(settings, public=True) as client:
        url = await _call(
            client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.minio_bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )
    return str(url)


async def head_object(key: str) -> dict[str, Any] | None:
    """Return size/content type/checksum metadata, or None when absent."""
    settings = get_settings()
    async with _client(settings) as client:
        try:
            return dict(await client.head_object(Bucket=settings.minio_bucket, Key=key))
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code", "")
            if status == 404 or code in {"NoSuchKey", "404", "NotFound"}:
                return None
            raise _storage_error(exc) from exc


async def read_object(key: str) -> bytes:
    settings = get_settings()
    async with _client(settings) as client:
        try:
            response = await client.get_object(Bucket=settings.minio_bucket, Key=key)
            body = response["Body"]
            try:
                return bytes(await body.read())
            finally:
                close = getattr(body, "close", None)
                if close is not None:
                    await _call(close())
        except ClientError as exc:
            raise _storage_error(exc) from exc


async def delete_object(key: str) -> None:
    settings = get_settings()
    async with _client(settings) as client:
        try:
            await client.delete_object(Bucket=settings.minio_bucket, Key=key)
        except ClientError as exc:
            raise _storage_error(exc) from exc
