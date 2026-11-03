"""M5 demo: credentials -> test -> sync -> worker -> per-resource result."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import httpx
from app.config import get_settings

BASE = "http://localhost:8080/api/v1"
TENANT = "acme"
EMAIL = "owner-acme@example.com"


def _run_worker() -> None:
    """Worker must run on the Compose network: credentials use internal URLs."""
    repo_root = Path(__file__).resolve().parents[2]
    docker = shutil.which("docker")
    if docker is None:
        raise SystemExit("docker is required to run the worker")
    subprocess.run(  # noqa: S603 - fixed argv, docker resolved above
        [
            docker,
            "compose",
            "run",
            "--rm",
            "-T",
            "worker",
            "python",
            "-m",
            "app.integrations.satusehat.worker",
            "--once",
        ],
        cwd=repo_root,
        check=True,
    )


def main() -> int:
    settings = get_settings()

    with httpx.Client(base_url=BASE, timeout=30) as client:
        login = client.post(
            "/auth/login",
            json={
                "tenant_slug": TENANT,
                "email": EMAIL,
                "password": settings.demo_password,
            },
        )
        login.raise_for_status()
        headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
            "X-Tenant-ID": TENANT,
        }

        saved = client.put(
            "/integrations/satusehat",
            headers=headers,
            json={
                "client_id": "demo-client",
                "client_secret": "demo-secret",
                "organization_id": "1000000001",
            },
        )
        saved.raise_for_status()
        print(f"credentials: status={saved.json()['status']} mode={saved.json()['mode']}")

        tested = client.post("/integrations/satusehat/test", headers=headers)
        tested.raise_for_status()
        print(
            "test:",
            tested.json()["status"],
            f"{tested.json().get('latency_ms')} ms",
        )

        _run_worker()

        queued = client.post(
            "/integrations/satusehat/sync",
            headers=headers,
            json={"kind": "organization"},
        )
        if queued.status_code == 409:
            _run_worker()
            queued = client.post(
                "/integrations/satusehat/sync",
                headers=headers,
                json={"kind": "organization"},
            )
        queued.raise_for_status()
        job_id = queued.json()["job_id"]
        print(f"job: {job_id} status={queued.json()['status']}")

    # The worker must run on the Compose network: stored credentials use the
    # internal mock hostname. A host process would fail DNS by design.
    _run_worker()

    with httpx.Client(base_url=BASE, timeout=30) as client:
        detail = client.get(
            f"/integrations/satusehat/jobs/{job_id}",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Tenant-ID": TENANT,
            },
        )
        detail.raise_for_status()
        job = detail.json()
        jobs = client.get(
            "/integrations/satusehat/jobs",
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
                "X-Tenant-ID": TENANT,
            },
        )
        jobs.raise_for_status()

    token = httpx.post(
        f"{settings.satusehat_mock_url}/oauth2/v1/accesstoken",
        data={
            "grant_type": "client_credentials",
            "client_id": "demo-client",
            "client_secret": "demo-secret",
        },
        timeout=10,
    )
    token.raise_for_status()
    print(f"token: {token.json()['access_token'][:12]}… (mock)")

    print()
    print(f"{'kind':<14}{'status':<10}{'attempts':<10}fhir_id")
    for item in jobs.json()["items"]:
        print(
            f"{item['kind']:<14}{item['status']:<10}"
            f"{item['attempts']:<10}{item.get('fhir_id') or '-'}"
        )
    print()
    print(f"job detail: status={job['status']} fhir_id={job.get('fhir_id')}")
    return 0 if job["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
