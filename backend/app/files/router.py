"""Tenant-scoped file uploads through presigned object-storage URLs."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import write_audit
from app.auth.dependencies import AuthUser, get_current_user, tenant_db
from app.auth.rate_limit import client_ip
from app.config import get_settings
from app.errors import AppError
from app.files.schemas import (
    DownloadResponse,
    FileList,
    FileOut,
    FileUsage,
    PresignUpload,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.observability import FILE_QUOTA_REJECTIONS_TOTAL, FILE_UPLOAD_BYTES_TOTAL
from app.observability_metrics import tenant_label
from app.pagination import decode_cursor, encode_cursor
from app.storage import delete_object, head_object, presign_get, presign_post, read_object

router = APIRouter(prefix="/api/v1/files", tags=["files"])

FILE_COLUMNS = """
    id, filename, content_type, size_bytes, status, sha256,
    owner_user_id, created_at, completed_at
"""


def clean_filename(name: str) -> tuple[str, str]:
    """Return (display name, safe key segment) from a client filename."""
    base = PurePosixPath(name.replace("\\", "/")).name.strip()
    if not base or base in {".", ".."} or "\x00" in base:
        raise AppError(status=422, code="invalid_filename", title="Invalid filename")
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._") or "file"
    return base[:255], safe[:120]


def object_key(tenant_id: UUID, file_id: UUID, safe_name: str) -> str:
    return f"tenants/{tenant_id}/{file_id}/{safe_name}"


def file_out(row: Any) -> FileOut:
    sha = row["sha256"]
    return FileOut(
        id=row["id"],
        filename=row["filename"],
        content_type=row["content_type"],
        size_bytes=row["size_bytes"],
        status=row["status"],
        sha256=sha.hex() if isinstance(sha, (bytes, bytearray)) else sha,
        owner_user_id=row["owner_user_id"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


def _tenant_of(user: AuthUser) -> Any:
    if user.tenant is None:
        raise AppError(status=403, code="tenant_required", title="A tenant is required")
    return user.tenant


@router.post(
    "/presign-upload",
    response_model=PresignUploadResponse,
    summary="Reserve quota and sign a direct upload",
)
async def presign_upload(
    body: PresignUploadRequest,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> PresignUploadResponse:
    settings = get_settings()
    tenant = _tenant_of(user)

    if body.size_bytes > settings.max_file_bytes:
        raise AppError(
            status=413,
            code="file_too_large",
            title="File is too large",
            detail=f"The maximum size is {settings.max_file_bytes} bytes.",
        )
    if body.content_type not in settings.allowed_content_types:
        raise AppError(
            status=415,
            code="unsupported_media_type",
            title="Unsupported media type",
            detail=f"Allowed types: {', '.join(settings.allowed_content_types)}.",
        )

    display_name, safe_name = clean_filename(body.filename)
    file_id = uuid4()
    key = object_key(tenant.id, file_id, safe_name)

    # Serialise quota reservations per tenant so two parallel presigns cannot
    # both observe the same free space.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"files:{tenant.id}"},
    )
    used = (
        await session.execute(
            text("SELECT COALESCE(SUM(size_bytes), 0) FROM files WHERE status <> 'deleted'")
        )
    ).scalar_one()
    if int(used) + body.size_bytes > settings.quota_bytes:
        FILE_QUOTA_REJECTIONS_TOTAL.inc()
        raise AppError(
            status=409,
            code="quota_exceeded",
            title="Storage quota exceeded",
            detail=f"The tenant quota is {settings.quota_bytes} bytes.",
        )

    await session.execute(
        text(
            """
            INSERT INTO files
                (id, tenant_id, owner_user_id, object_key, filename,
                 content_type, size_bytes)
            VALUES
                (:id, :tenant_id, :owner, :key, :filename, :content_type, :size)
            """
        ),
        {
            "id": file_id,
            "tenant_id": tenant.id,
            "owner": user.id,
            "key": key,
            "filename": display_name,
            "content_type": body.content_type,
            "size": body.size_bytes,
        },
    )

    post = await presign_post(
        key=key,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        expires_in=settings.upload_url_ttl_seconds,
    )

    return PresignUploadResponse(
        file_id=file_id,
        upload=PresignUpload(
            url=post["url"],
            fields=post["fields"],
            expires_in=settings.upload_url_ttl_seconds,
        ),
        max_size_bytes=settings.max_file_bytes,
    )


@router.post(
    "/{file_id}/complete",
    response_model=FileOut,
    summary="Verify an uploaded object and mark it ready",
)
async def complete_upload(
    file_id: UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> FileOut:
    settings = get_settings()
    tenant = _tenant_of(user)

    row = (
        (
            await session.execute(
                text(
                    f"""
                SELECT {FILE_COLUMNS}, object_key,
                       created_at < now() - (CAST(:ttl AS integer) * interval '1 second') AS expired
                  FROM files
                 WHERE id = :file_id AND status <> 'deleted'
                 FOR UPDATE
                """  # noqa: S608 - column list is a module constant
                ),
                {"file_id": file_id, "ttl": settings.upload_url_ttl_seconds},
            )
        )
        .mappings()
        .first()
    )

    if row is None:
        raise AppError(status=404, code="file_not_found", title="File not found")
    if user.role == "member" and row["owner_user_id"] != user.id:
        raise AppError(status=404, code="file_not_found", title="File not found")
    if row["status"] == "ready":
        raise AppError(status=409, code="already_completed", title="Upload is already complete")
    if row["expired"]:
        raise AppError(
            status=410,
            code="upload_expired",
            title="The upload window has expired",
        )

    head = await head_object(row["object_key"])
    if head is None:
        raise AppError(
            status=404,
            code="object_not_found",
            title="The uploaded object was not found",
        )

    size = int(head.get("ContentLength", -1))
    if size != row["size_bytes"]:
        raise AppError(
            status=409,
            code="size_mismatch",
            title="Uploaded size does not match the reservation",
        )

    stored_type = str(head.get("ContentType", "")).split(";", 1)[0].strip().lower()
    if stored_type != row["content_type"].lower():
        raise AppError(
            status=409,
            code="content_type_mismatch",
            title="Uploaded content type does not match the reservation",
        )

    data = await read_object(row["object_key"])
    digest = hashlib.sha256(data).hexdigest()

    updated = (
        (
            await session.execute(
                text(
                    f"""
                UPDATE files
                   SET status = 'ready',
                       sha256 = :sha256,
                       completed_at = now()
                 WHERE id = :file_id
             RETURNING {FILE_COLUMNS}
                """  # noqa: S608 - column list is a module constant
                ),
                {"sha256": bytes.fromhex(digest), "file_id": file_id},
            )
        )
        .mappings()
        .one()
    )

    FILE_UPLOAD_BYTES_TOTAL.labels(tenant_label(tenant.slug)).inc(size)

    await write_audit(
        session,
        "file.completed",
        tenant_id=tenant.id,
        actor_user_id=user.id,
        ip=client_ip(request),
        metadata={
            "file_id": str(file_id),
            "filename": row["filename"],
            "size_bytes": size,
        },
    )

    return file_out(updated)


@router.get("/usage", response_model=FileUsage, summary="Tenant storage usage")
async def file_usage(
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> FileUsage:
    _tenant_of(user)
    row = (
        (
            await session.execute(
                text(
                    """
                SELECT count(*) AS files,
                       COALESCE(SUM(size_bytes), 0) AS used_bytes
                  FROM files
                 WHERE status <> 'deleted'
                """
                )
            )
        )
        .mappings()
        .one()
    )
    return FileUsage(
        files=int(row["files"]),
        used_bytes=int(row["used_bytes"]),
        quota_bytes=get_settings().quota_bytes,
    )


@router.get(
    "/{file_id}/download",
    response_model=DownloadResponse,
    summary="Issue a short-lived download URL",
)
async def download_file(
    file_id: UUID,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> DownloadResponse:
    row = (
        await session.execute(
            text(
                """
                SELECT object_key FROM files
                 WHERE id = :file_id AND status = 'ready'
                """
            ),
            {"file_id": file_id},
        )
    ).first()
    if row is None:
        raise AppError(status=404, code="file_not_found", title="File not found")

    settings = get_settings()
    url = await presign_get(key=row[0], expires_in=settings.download_url_ttl_seconds)
    return DownloadResponse(url=url, expires_in=settings.download_url_ttl_seconds)


@router.get("", response_model=FileList, summary="List files, newest first")
async def list_files(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
    status: Literal["uploading", "ready", "deleted"] | None = None,
    owner: UUID | None = None,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> FileList:
    tenant = _tenant_of(user)
    is_admin = user.role in {"owner", "admin"}

    params: dict[str, Any] = {"tenant_id": tenant.id, "limit": limit + 1}
    filters: list[str] = ["tenant_id = :tenant_id"]

    if status is None:
        filters.append("status <> 'deleted'")
    else:
        filters.append("status = :status")
        params["status"] = status

    if owner is not None:
        if not is_admin and owner != user.id:
            raise AppError(
                status=403,
                code="insufficient_role",
                title="Only admins can list another user's files",
            )
        filters.append("owner_user_id = :owner")
        params["owner"] = owner
    elif not is_admin:
        filters.append("owner_user_id = :owner")
        params["owner"] = user.id

    order_after = ""
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        order_after = "AND (created_at, id) < (:cursor_ts, :cursor_id)"
        params["cursor_ts"] = cursor_ts
        params["cursor_id"] = cursor_id

    query = f"""
        SELECT {FILE_COLUMNS}
          FROM files
         WHERE {" AND ".join(filters)} {order_after}
         ORDER BY created_at DESC, id DESC
         LIMIT :limit
    """  # noqa: S608 - filters are fixed internal fragments
    rows = (await session.execute(text(query), params)).mappings().all()

    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        next_cursor = encode_cursor(page[-1]["created_at"], page[-1]["id"])

    return FileList(
        items=[file_out(row) for row in page],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.delete("/{file_id}", status_code=204, summary="Soft-delete a file")
async def delete_file(
    file_id: UUID,
    request: Request,
    user: AuthUser = Depends(get_current_user),
    session: AsyncSession = Depends(tenant_db),
) -> Response:
    tenant = _tenant_of(user)
    row = (
        (
            await session.execute(
                text(
                    """
                SELECT id, owner_user_id, object_key, filename, status FROM files
                 WHERE id = :file_id
                 FOR UPDATE
                """
                ),
                {"file_id": file_id},
            )
        )
        .mappings()
        .first()
    )

    if row is None:
        raise AppError(status=404, code="file_not_found", title="File not found")
    if row["status"] == "deleted":
        return Response(status_code=204)

    if user.role == "member" and row["owner_user_id"] != user.id:
        raise AppError(status=404, code="file_not_found", title="File not found")

    await session.execute(
        text(
            """
            UPDATE files SET status = 'deleted', deleted_at = now()
             WHERE id = :file_id
            """
        ),
        {"file_id": file_id},
    )
    await delete_object(row["object_key"])
    await write_audit(
        session,
        "file.deleted",
        tenant_id=tenant.id,
        actor_user_id=user.id,
        ip=client_ip(request),
        metadata={"file_id": str(file_id), "filename": row["filename"]},
    )
    return Response(status_code=204)
