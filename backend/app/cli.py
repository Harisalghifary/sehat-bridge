"""Operator CLI: provision tenants and fan out migrations."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.tenancy import service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    tenant = sub.add_parser("tenant", help="provision a tenant")
    tenant.add_argument("--slug", required=True)
    tenant.add_argument("--name", required=True)
    tenant.add_argument("--owner", required=True, help="owner email")
    tenant.add_argument("--display-name")

    sub.add_parser("migrate-tenants", help="apply pending tenant migrations")
    sub.add_parser("list-tenants", help="list tenants")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.command == "tenant":
        tenant = await service.provision_tenant(
            slug=args.slug,
            name=args.name,
            owner_email=args.owner,
            owner_display_name=args.display_name,
        )
        print(f"tenant {tenant.slug} ready: schema={tenant.schema} id={tenant.id}")
        return 0

    if args.command == "migrate-tenants":
        results = await service.migrate_all_tenants()
        if not results:
            print("no active tenants")
        for slug, applied in results:
            state = ", ".join(applied) if applied else "up to date"
            print(f"{slug}: {state}")
        return 0

    tenants = await service.list_tenants()
    print(service.describe(tenants) if tenants else "no tenants")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
