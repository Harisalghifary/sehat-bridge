"""Capture the nine documentation screenshots from the running stack.

Usage (from the repository root):
    make screenshots
    make screenshots ARGS="--only beranda,dasbor"

The harness seeds deterministic rows into the `acme` tenant, drives the real UI
with Playwright, and writes docs/screenshots/*.png.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "screenshots"
SITE = "http://localhost:8080"
PASSWORD = "demo-password-123"

SEED_SQL = """
SET search_path = tenant_acme, public;
INSERT INTO files (id, tenant_id, owner_user_id, object_key, filename,
                   content_type, size_bytes, status, created_at, completed_at)
SELECT '11111111-1111-4111-8111-111111111111', t.id, u.id,
       'tenants/' || t.id || '/11111111-1111-4111-8111-111111111111/rencana-klinik.pdf',
       'rencana-klinik.pdf', 'application/pdf', 482133, 'ready',
       now() - interval '2 hours', now() - interval '2 hours'
  FROM public.tenants t
  JOIN public.memberships m ON m.tenant_id = t.id AND m.role = 'owner'
  JOIN public.users u ON u.id = m.user_id
 WHERE t.slug = 'acme'
ON CONFLICT (id) DO NOTHING;

INSERT INTO files (id, tenant_id, owner_user_id, object_key, filename,
                   content_type, size_bytes, status, created_at, completed_at)
SELECT '22222222-2222-4222-8222-222222222222', t.id, u.id,
       'tenants/' || t.id || '/22222222-2222-4222-8222-222222222222/daftar-obat.csv',
       'daftar-obat.csv', 'text/csv', 12840, 'ready',
       now() - interval '1 day', now() - interval '1 day'
  FROM public.tenants t
  JOIN public.memberships m ON m.tenant_id = t.id AND m.role = 'owner'
  JOIN public.users u ON u.id = m.user_id
 WHERE t.slug = 'acme'
ON CONFLICT (id) DO NOTHING;

INSERT INTO files (id, tenant_id, owner_user_id, object_key, filename,
                   content_type, size_bytes, status, created_at)
SELECT '44444444-4444-4444-8444-444444444444', t.id, u.id,
       'tenants/' || t.id || '/44444444-4444-4444-8444-444444444444/laporan-bulanan.pdf',
       'laporan-bulanan.pdf', 'application/pdf', 912400, 'uploading', now()
  FROM public.tenants t
  JOIN public.memberships m ON m.tenant_id = t.id AND m.role = 'owner'
  JOIN public.users u ON u.id = m.user_id
 WHERE t.slug = 'acme'
ON CONFLICT (id) DO NOTHING;

INSERT INTO integration_credentials
       (provider, client_id, client_secret_enc, organization_id, base_url,
        status, last_verified_at)
VALUES ('satusehat', 'demo-client', '\\x00'::bytea, 'demo-org',
        'http://mock-satusehat:8090/fhir-r4/v1', 'connected', now() - interval '3 hours')
ON CONFLICT (provider) DO UPDATE
   SET status = 'connected', last_error = NULL;

INSERT INTO sync_jobs (id, tenant_id, kind, local_id, payload, status,
                       attempts, last_error, created_at, updated_at)
SELECT '33333333-3333-4333-8333-333333333333', t.id, 'organization', t.id,
       '{"organization_id": "demo-org"}'::jsonb, 'failed', 1,
       'Mock returned HTTP 400: Organization.identifier tidak valid',
       now() - interval '4 hours', now() - interval '4 hours'
  FROM public.tenants t WHERE t.slug = 'acme'
ON CONFLICT (id) DO NOTHING;
"""


def seed() -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-q",
            "-U",
            "sehat",
            "-d",
            "sehat",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=SEED_SQL,
        text=True,
        cwd=ROOT,
        check=True,
    )


def disable_motion(page) -> None:
    page.add_style_tag(
        content="""
        *, *::before, *::after { animation: none !important; transition: none !important; }
        ::-webkit-scrollbar { display: none; }
        """
    )


def optimize(path: Path, *, width: int) -> None:
    """Export at the documented width and keep each PNG under the 250 KB budget."""
    image = Image.open(path).convert("RGB")
    if image.width > width:
        height = round(image.height * width / image.width)
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(path, optimize=True)
    if path.stat().st_size > 250 * 1024:
        image.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(
            path, optimize=True
        )
    if path.stat().st_size > 250 * 1024:
        width = 1200
        height = round(image.height * width / image.width)
        smaller = image.resize((width, height), Image.Resampling.LANCZOS)
        smaller.quantize(
            colors=128, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        ).save(path, optimize=True)


def shot(page, name: str, *, full_page: bool = True, width: int = 1440) -> Path:
    path = OUT / f"{name}.png"
    page.wait_for_load_state("load")
    try:
        page.locator("h1").first.wait_for(state="visible", timeout=15000)
    except Exception:
        pass
    disable_motion(page)
    page.screenshot(path=str(path), full_page=full_page, animations="disabled")
    optimize(path, width=width)
    return path


def faskes_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,
        locale="id-ID",
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.goto(f"{SITE}/masuk")
    page.get_by_label("Kode faskes").fill("acme")
    page.get_by_label("Email").fill("owner-acme@example.com")
    page.get_by_label("Kata sandi").fill(PASSWORD)
    page.get_by_role("button", name="Masuk").click()
    page.wait_for_url("**/app/dasbor")
    return context


def ops_context(browser: Browser) -> BrowserContext:
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,
        locale="id-ID",
        reduced_motion="reduce",
    )
    page = context.new_page()
    page.goto(f"{SITE}/ops/masuk")
    page.get_by_label("Email operator").fill("ops@sehatbridge.dev")
    page.get_by_label("Kata sandi").fill(PASSWORD)
    page.get_by_role("button", name="Masuk ke konsol").click()
    page.wait_for_url("**/ops/tenant")
    return context


def capture_all(only: set[str] | None, playwright: Playwright) -> list[Path]:
    browser = playwright.chromium.launch()
    written: list[Path] = []
    marketing = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,
        locale="id-ID",
        reduced_motion="reduce",
    )
    page = marketing.new_page()

    def want(name: str) -> bool:
        return only is None or name in only

    if want("cover"):
        page.set_viewport_size({"width": 1280, "height": 640})
        page.goto(f"{SITE}/")
        written.append(shot(page, "cover", full_page=False, width=1280))
        page.set_viewport_size({"width": 1440, "height": 900})

    if want("beranda"):
        page.goto(f"{SITE}/")
        written.append(shot(page, "01-beranda", full_page=False))

    if want("solusi"):
        page.goto(f"{SITE}/solusi")
        written.append(shot(page, "02-solusi"))

    if want("integrasi"):
        page.goto(f"{SITE}/integrasi")
        written.append(shot(page, "03-integrasi"))

    if want("mobile-beranda"):
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            locale="id-ID",
            reduced_motion="reduce",
        )
        mpage = mobile.new_page()
        mpage.goto(f"{SITE}/")
        written.append(shot(mpage, "08-mobile-beranda", full_page=False, width=390))
        mobile.close()

    marketing.close()

    if any(want(name) for name in ("dasbor", "berkas", "integrasi-app")):
        app_context = faskes_context(browser)
        app_page = app_context.new_page()
        if want("dasbor"):
            app_page.goto(f"{SITE}/app/dasbor")
            written.append(shot(app_page, "04-dasbor"))
        if want("berkas"):
            app_page.goto(f"{SITE}/app/berkas")
            written.append(shot(app_page, "05-berkas"))
        if want("integrasi-app"):
            app_page.goto(f"{SITE}/app/integrasi")
            written.append(shot(app_page, "06-integrasi-app"))
        app_context.close()

    if want("ops-tenant"):
        ops = ops_context(browser)
        ops_page = ops.new_page()
        ops_page.goto(f"{SITE}/ops/tenant")
        written.append(shot(ops_page, "07-ops-tenant"))
        ops.close()
    browser.close()
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated names, e.g. beranda,dasbor")
    parser.add_argument("--check", action="store_true", help="capture to a temp dir")
    parser.add_argument("--no-seed", action="store_true", help="skip demo row seeding")
    args = parser.parse_args()

    only = set(args.only.split(",")) if args.only else None
    if not args.no_seed:
        seed()

    if args.check:
        global OUT
        OUT = Path(tempfile.mkdtemp(prefix="sehat-bridge-shots-"))
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        written = capture_all(only, playwright)

    for path in written:
        size_kb = path.stat().st_size / 1024
        print(f"[ok] {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path} "
              f"({size_kb:.0f} KB)")
        if size_kb > 250:
            print("  warning: larger than the 250 KB target", file=sys.stderr)

    if args.check:
        print(f"check output kept in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())