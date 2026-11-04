"""Redis-backed idempotency for mutating API requests.

A client sends ``Idempotency-Key`` on POST/PUT/PATCH/DELETE. The first response
is stored for 24 hours keyed by the key, request fingerprint, and credentials.
A replay returns the exact status/body and adds ``Idempotency-Replayed: true``.
Reusing a key with a different payload is a ``409`` instead of silently
returning unrelated data.

Auth routes are excluded because replaying token material across requests is a
security risk, and they already have their own rotation semantics.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
EXCLUDED_PREFIXES = ("/api/v1/auth/",)
MAX_BODY_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024


def _fingerprint(scope: dict[str, Any], body: bytes) -> str:
    headers = {key.lower(): value for key, value in scope.get("headers", [])}
    digest = hashlib.sha256()
    digest.update(headers.get(b"authorization", b"")[:4096])
    digest.update(scope.get("method", "").encode())
    digest.update(scope.get("path", "").encode())
    digest.update(scope.get("query_string", b""))
    digest.update(body)
    return digest.hexdigest()


class IdempotencyMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        path = scope.get("path", "")
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        key = headers.get(b"idempotency-key", b"").decode("latin-1").strip()[:200]

        if (
            method not in MUTATING
            or not key
            or not path.startswith("/api/")
            or path.startswith(EXCLUDED_PREFIXES)
        ):
            await self.app(scope, receive, send)
            return

        body = await self._read_body(receive)
        if len(body) > MAX_BODY_BYTES:
            await self.app(scope, self._replay(body), send)
            return

        app = scope.get("app")
        redis = getattr(getattr(app, "state", None), "redis", None)
        fingerprint = _fingerprint(scope, body)
        cache_key = f"sb:idem:{hashlib.sha256(key.encode()).hexdigest()}"

        if redis is not None:
            try:
                stored_raw = await redis.get(cache_key)
                if stored_raw:
                    stored = json.loads(stored_raw)
                    if stored.get("fingerprint") != fingerprint:
                        await self._problem(
                            scope,
                            send,
                            status=422,
                            code="idempotency_key_reuse",
                            title="Idempotency key reused with a different request",
                        )
                        return
                    await self._send_stored(send, stored)
                    return
            except Exception:
                logger.warning("idempotency read failed", exc_info=True)

        status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        chunks: list[bytes] = []
        size = 0
        too_large = False

        async def capture(message: dict[str, Any]) -> None:
            nonlocal status, response_headers, size, too_large
            if message["type"] == "http.response.start":
                status = int(message["status"])
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    too_large = True
                chunks.append(chunk)
            await send(message)

        await self.app(scope, self._replay(body), capture)

        if redis is not None and 200 <= status < 300 and not too_large:
            stored = {
                "fingerprint": fingerprint,
                "status": status,
                "headers": [
                    [k.decode("latin-1"), v.decode("latin-1")]
                    for k, v in response_headers
                    if k.lower() not in {b"content-length", b"transfer-encoding", b"connection"}
                ],
                "body": base64.b64encode(b"".join(chunks)).decode(),
            }
            try:
                await redis.set(
                    cache_key,
                    json.dumps(stored),
                    ex=get_settings().idempotency_ttl_seconds,
                )
            except Exception:
                logger.warning("idempotency write failed", exc_info=True)

    @staticmethod
    async def _read_body(receive: Any) -> bytes:
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return bytes(body)

    @staticmethod
    def _replay(body: bytes) -> Any:
        sent = False

        async def receive() -> dict[str, Any]:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        return receive

    async def _send_stored(self, send: Any, stored: dict[str, Any]) -> None:
        headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in stored["headers"]]
        headers.append((b"idempotency-replayed", b"true"))
        await send(
            {
                "type": "http.response.start",
                "status": stored["status"],
                "headers": headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": base64.b64decode(stored["body"]),
                "more_body": False,
            }
        )

    async def _problem(
        self,
        scope: dict[str, Any],
        send: Any,
        *,
        status: int,
        code: str,
        title: str,
    ) -> None:
        body = json.dumps(
            {
                "type": f"https://sehatbridge.dev/errors/{code}",
                "title": title,
                "status": status,
                "code": code,
                "trace_id": scope.get("state", {}).get("request_id"),
                "details": [],
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"idempotency-replayed", b"false"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})
