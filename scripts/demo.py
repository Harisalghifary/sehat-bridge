"""Live acceptance demo: one pass/fail line per product claim.

Run through `make demo` so the backend virtualenv and working directory are set.
The script provisions disposable tenants, exercises the real UI API, then drops
everything it created.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import asyncpg
import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.db.engine import asyncpg_dsn
from app.db.tenant_context import schema_name

BASE = "http://localhost:8080"
API = f"{BASE}/api/v1"
MOCK = "http://localhost:8090"
PASSWORD = "demo-password-123"
SECRET = "demo-secret-do-not-print-123"

created: list[tuple[str, str]] = []
created_leads: list[str] = []


def ok(label: str, detail: str = "") -> None:
    print(f"[ok] {label}{(': ' + detail) if detail else ''}", flush=True)


async def fail(label: str, detail: str) -> None:
    print(f"[fail] {label}: {detail}", flush=True)
    raise SystemExit(1)


def expect(response: httpx.Response, status: int, label: str) -> httpx.Response:
    if response.status_code != status:
        raise RuntimeError(f"{label} -> {response.status_code}: {response.text[:500]}")
    return response


async def db():
    settings = get_settings()
    return await asyncpg.connect(asyncpg_dsn(settings.migration_database_url))


async def cleanup() -> None:
    conn = await db()
    try:
        for slug, owner in created:
            await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name(slug)}" CASCADE')
            await conn.execute("DELETE FROM public.tenants WHERE slug = $1", slug)
            await conn.execute("DELETE FROM public.users WHERE email = $1", owner)
        for email in created_leads:
            await conn.execute("DELETE FROM public.leads WHERE email = $1", email)
    finally:
        await conn.close()


async def login(client: httpx.AsyncClient, slug: str, email: str, password: str = PASSWORD):
    response = await client.post(
        f"{API}/auth/login",
        json={"tenant_slug": slug, "email": email, "password": password},
    )
    expect(response, 200, f"login {slug}")
    return response.json()


async def provision(client: httpx.AsyncClient, ops_token: str, slug: str, owner: str) -> None:
    response = await client.post(
        f"{API}/admin/tenants",
        headers={"authorization": f"Bearer {ops_token}"},
        json={
            "slug": slug,
            "name": f"Demo {slug}",
            "owner_email": owner,
            "owner_display_name": "Demo Owner",
            "password": PASSWORD,
        },
    )
    expect(response, 201, f"provision {slug}")
    assert response.json()["tenant"]["status"] == "active"
    created.append((slug, owner))


async def wait_job(
    client: httpx.AsyncClient,
    token: str,
    slug: str,
    job_id: str,
    *,
    target: set[str],
    timeout: float = 45.0,
):
    deadline = asyncio.get_event_loop().time() + timeout
    last: dict[str, Any] = {}
    while asyncio.get_event_loop().time() < deadline:
        response = await client.get(
            f"{API}/integrations/satusehat/jobs/{job_id}",
            headers={"authorization": f"Bearer {token}", "x-tenant-id": slug},
        )
        if response.status_code == 200:
            last = response.json()
            if last["status"] in target:
                return last
        await asyncio.sleep(0.5)
    raise RuntimeError(f"job {job_id} did not reach {target}; last={last}")


async def main() -> int:
    subprocess.run(["docker", "compose", "up", "-d", "worker"], check=False,
                   capture_output=True)
    suffix = uuid.uuid4().hex[:6]
    klinik = f"demo-klinik-{suffix}"
    lab = f"demo-lab-{suffix}"
    klinik_owner = f"owner-{klinik}@example.com"
    lab_owner = f"owner-{lab}@example.com"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            health = expect(await client.get(f"{API}/health/ready"), 200, "readiness")
            checks = health.json()["checks"]
            assert all(value == "ok" for value in checks.values()), checks
            ok("health", "postgres, redis, minio")

            home = expect(await client.get(f"{BASE}/"), 200, "marketing")
            assert "Sehat Bridge" in home.text
            expect(await client.get(f"{BASE}/sitemap.xml"), 200, "sitemap")
            ok("marketing", "/ returns 200, sitemap present")

            lead_email = f"demo-lead-{suffix}@example.com"
            created_leads.append(lead_email)
            lead = await client.post(
                f"{API}/leads",
                headers={"x-forwarded-for": f"10.{int(suffix, 16) % 250}.9.7"},
                json={
                    "name": "Demo Lead",
                    "email": lead_email,
                    "facility_name": "Klinik Demo",
                    "facility_type": "klinik",
                    "city": "Bandung",
                    "message": "Demo run",
                    "website": "",
                    "elapsed_ms": 5000,
                },
            )
            expect(lead, 202, "lead")
            conn = await db()
            try:
                row = await conn.fetchval(
                    "SELECT id FROM public.leads WHERE email = $1", lead_email
                )
            finally:
                await conn.close()
            assert row is not None
            ok("lead captured", "row written by the public form API")

            platform = await client.post(
                f"{API}/auth/platform-login",
                json={"email": "ops@sehatbridge.dev", "password": PASSWORD},
            )
            if platform.status_code != 200:
                await fail("operator login", "seed the demo data with `make seed`")
            ops_token = platform.json()["access_token"]
            await provision(client, ops_token, klinik, klinik_owner)
            await provision(client, ops_token, lab, lab_owner)
            ok("tenant provisioned", f"{klinik}, {lab}")

            shared_acme = await login(client, "acme", "same@person.dev")
            shared_globex = await login(client, "globex", "same@person.dev")
            assert shared_acme["scope"] == "tenant" and shared_globex["scope"] == "tenant"
            ok("shared identity", "one email joins acme and globex")

            acme_owner = await login(client, "acme", "owner-acme@example.com")
            forged = await client.get(
                f"{API}/users/me",
                headers={
                    "authorization": f"Bearer {acme_owner['access_token']}",
                    "x-tenant-id": "globex",
                },
            )
            assert forged.status_code == 403
            assert forged.json()["code"] == "tenant_mismatch"
            ok("forged X-Tenant-ID rejected", "403 tenant_mismatch")

            member_denied = await client.patch(
                f"{API}/users/{uuid.uuid4()}/role",
                headers={
                    "authorization": f"Bearer {shared_globex['access_token']}",
                    "x-tenant-id": "globex",
                },
                json={"role": "admin"},
            )
            assert member_denied.status_code == 403
            ok("member cannot change roles", "403 insufficient_role")

            me = await client.get(
                f"{API}/users/me",
                headers={
                    "authorization": f"Bearer {acme_owner['access_token']}",
                    "x-tenant-id": "acme",
                },
            )
            owner_id = me.json()["id"]
            last_owner = await client.patch(
                f"{API}/users/{owner_id}/role",
                headers={
                    "authorization": f"Bearer {acme_owner['access_token']}",
                    "x-tenant-id": "acme",
                },
                json={"role": "member"},
            )
            assert last_owner.status_code == 409
            assert last_owner.json()["code"] == "last_owner"
            ok("last owner protected", "409 last_owner")

            headers = {
                "authorization": f"Bearer {acme_owner['access_token']}",
                "x-tenant-id": "acme",
            }
            content = b"demo evidence\n"
            presign = expect(
                await client.post(
                    f"{API}/files/presign-upload",
                    headers={**headers, "idempotency-key": str(uuid.uuid4())},
                    json={
                        "filename": f"demo-{suffix}.txt",
                        "size_bytes": len(content),
                        "content_type": "text/plain",
                    },
                ),
                200,
                "presign",
            ).json()
            upload = presign["upload"]
            multipart: dict[str, Any] = {
                key: (None, value) for key, value in upload["fields"].items()
            }
            multipart["file"] = (f"demo-{suffix}.txt", content, "text/plain")
            stored = await client.post(upload["url"], files=multipart)
            assert stored.status_code in {200, 204}, stored.text
            completed = expect(
                await client.post(
                    f"{API}/files/{presign['file_id']}/complete",
                    headers={**headers, "idempotency-key": str(uuid.uuid4())},
                ),
                200,
                "complete",
            ).json()
            download = await client.get(
                f"{API}/files/{completed['id']}/download", headers=headers
            )
            expect(download, 200, "download")
            fetched = await client.get(download.json()["url"])
            assert fetched.content == content
            ok("file uploaded, completed, downloaded", "byte-for-byte match")

            small = expect(
                await client.post(
                    f"{API}/files/presign-upload",
                    headers=headers,
                    json={
                        "filename": f"oversize-{suffix}.txt",
                        "size_bytes": 10,
                        "content_type": "text/plain",
                    },
                ),
                200,
                "oversize presign",
            ).json()
            fields = {key: (None, value) for key, value in small["upload"]["fields"].items()}
            fields["file"] = ("oversize.txt", b"x" * 32, "text/plain")
            rejected = await client.post(small["upload"]["url"], files=fields)
            assert rejected.status_code >= 400, rejected.text
            ok("oversize upload rejected", "storage policy, not app code")
            for file_id in (completed["id"], small["file_id"]):
                await client.delete(f"{API}/files/{file_id}", headers=headers)

            mock_token = await client.post(
                f"{MOCK}/oauth2/v1/accesstoken",
                data={
                    "grant_type": "client_credentials",
                    "client_id": "demo-client",
                    "client_secret": "demo-secret",
                },
            )
            expect(mock_token, 200, "mock token")
            assert mock_token.json()["access_token"]
            ok("satusehat mock token issued", "oauth2 client_credentials")

            temp_headers = {
                "authorization": f"Bearer {(await login(client, klinik, klinik_owner))['access_token']}",
                "x-tenant-id": klinik,
            }
            creds = await client.put(
                f"{API}/integrations/satusehat",
                headers=temp_headers,
                json={
                    "client_id": "demo-client",
                    "client_secret": SECRET,
                    "organization_id": "demo-org",
                },
            )
            expect(creds, 200, "credentials")
            tested = await client.post(
                f"{API}/integrations/satusehat/test", headers=temp_headers
            )
            expect(tested, 200, "test connection")
            assert tested.json()["status"] == "connected", tested.text
            job = await client.post(
                f"{API}/integrations/satusehat/sync",
                headers=temp_headers,
                json={"kind": "organization"},
            )
            expect(job, 202, "enqueue organization")
            done = await wait_job(
                client,
                temp_headers["authorization"].split(" ", 1)[1],
                klinik,
                job.json()["job_id"],
                target={"done"},
            )
            ok("satusehat organization synced", f"id={done.get('fhir_id', 'n/a')}")

            lab_headers = {
                "authorization": f"Bearer {(await login(client, lab, lab_owner))['access_token']}",
                "x-tenant-id": lab,
            }
            await client.put(
                f"{API}/integrations/satusehat",
                headers=lab_headers,
                json={
                    "client_id": "demo-client",
                    "client_secret": SECRET,
                    "organization_id": "demo-org",
                },
            )
            await client.post(f"{API}/integrations/satusehat/test", headers=lab_headers)

            conn = await db()
            try:
                await conn.execute(
                    f'UPDATE "{schema_name(lab)}".integration_credentials '
                    "SET base_url = base_url || '?fail=500'"
                )
            finally:
                await conn.close()

            retry_job = await client.post(
                f"{API}/integrations/satusehat/sync",
                headers=lab_headers,
                json={"kind": "organization"},
            )
            expect(retry_job, 202, "enqueue retry")
            retry_id = retry_job.json()["job_id"]
            # Wait for the first failed attempt, then make the mock healthy.
            deadline = asyncio.get_event_loop().time() + 30
            attempts = 0
            while asyncio.get_event_loop().time() < deadline:
                detail = await client.get(
                    f"{API}/integrations/satusehat/jobs/{retry_id}",
                    headers=lab_headers,
                )
                attempts = detail.json()["attempts"]
                if attempts >= 1:
                    break
                await asyncio.sleep(0.5)
            assert attempts >= 1, "worker never claimed the retry job"
            conn = await db()
            try:
                await conn.execute(
                    f'UPDATE "{schema_name(lab)}".integration_credentials '
                    "SET base_url = replace(base_url, '?fail=500', '')"
                )
            finally:
                await conn.close()
            await wait_job(
                client,
                lab_headers["authorization"].split(" ", 1)[1],
                lab,
                retry_id,
                target={"done"},
            )
            ok("satusehat 500 retried", "job done after the mock recovered")

            conn = await db()
            try:
                await conn.execute(
                    f'UPDATE "{schema_name(lab)}".integration_credentials '
                    "SET base_url = base_url || '?fail=4xx'"
                )
            finally:
                await conn.close()
            bad_job = await client.post(
                f"{API}/integrations/satusehat/sync",
                headers=lab_headers,
                json={"kind": "patient"},
            )
            expect(bad_job, 202, "enqueue terminal 4xx")
            failed = await wait_job(
                client,
                lab_headers["authorization"].split(" ", 1)[1],
                lab,
                bad_job.json()["job_id"],
                target={"failed"},
            )
            assert failed["attempts"] == 1, failed
            ok("satusehat 4xx failed without retry", "attempts=1")

            conn = await db()
            try:
                leaked = await conn.fetchval(
                    "SELECT count(*) FROM public.audit_log "
                    "WHERE metadata::text LIKE '%' || $1 || '%'",
                    SECRET,
                )
            finally:
                await conn.close()
            assert leaked == 0
            fetched_creds = await client.get(
                f"{API}/integrations/satusehat", headers=lab_headers
            )
            assert SECRET not in fetched_creds.text
            logs = subprocess.run(
                ["docker", "compose", "logs", "--no-color", "backend", "worker"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            assert SECRET not in logs
            ok("secret absent from diagnostics", "not in responses, audit, or logs")

        return 0
    finally:
        await cleanup()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))