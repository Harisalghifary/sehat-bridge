"""Operator CLI: provision tenants and fan out migrations."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.auth.security import hash_password
from app.config import get_settings
from app.tenancy import service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    tenant = sub.add_parser("tenant", help="provision a tenant")
    tenant.add_argument("--slug", required=True)
    tenant.add_argument("--name", required=True)
    tenant.add_argument("--owner", required=True, help="owner email")
    tenant.add_argument("--display-name")
    tenant.add_argument("--password")

    sub.add_parser("migrate-tenants", help="apply pending tenant migrations")
    sub.add_parser("list-tenants", help="list tenants")
    sub.add_parser("sweep", help="remove expired uploads and release quota")
    sub.add_parser("retention", help="delete expired audit rows, leads, and tokens")

    rewrap = sub.add_parser(
        "rewrap-secrets", help="re-encrypt integration secrets with the current key"
    )
    rewrap.add_argument(
        "--old-key",
        required=True,
        help="previous APP_ENCRYPTION_KEY passphrase",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.command == "tenant":
        settings = get_settings()
        password = args.password or settings.demo_password
        tenant = await service.provision_tenant(
            slug=args.slug,
            name=args.name,
            owner_email=args.owner,
            owner_display_name=args.display_name,
            password_hash=hash_password(password),
        )
        print(f"tenant {tenant.slug} ready: schema={tenant.schema} id={tenant.id}")
        await service.ensure_password_for_email(args.owner, hash_password(password))
        print(f"owner login: {args.owner} / {password}")
        return 0

    if args.command == "migrate-tenants":
        results = await service.migrate_all_tenants()
        if not results:
            print("no active tenants")
        for slug, applied in results:
            state = ", ".join(applied) if applied else "up to date"
            print(f"{slug}: {state}")
        return 0

    if args.command == "sweep":
        from app.files.sweep import sweep_expired

        removed = await sweep_expired()
        print(f"sweep: removed {removed} expired upload(s)")
        return 0

    if args.command == "retention":
        from app.maintenance import run_retention

        counts = await run_retention()
        print(
            "retention: "
            f"audit_rows={counts['audit_rows']} leads={counts['leads']} "
            f"tokens={counts['auth_tokens']}"
        )
        return 0

    if args.command == "rewrap-secrets":
        from app.integrations.satusehat.rotate import rewrap_secrets

        count = await rewrap_secrets(args.old_key)
        print(f"rewrap-secrets: re-encrypted {count} credential(s)")
        return 0

    tenants = await service.list_tenants()
    print(service.describe(tenants) if tenants else "no tenants")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
