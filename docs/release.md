# Release checklist — v0.1.0

Run from a clean checkout with Docker running. Do not tag until every box passes.

## 1. Code and data

- [ ] `git status` is clean on `main`; CI is green on the same commit.
- [ ] `make up && make migrate && make seed` completes.
- [ ] `make test` passes (unit, ESLint, TypeScript).
- [ ] `make test-integration` passes (Postgres, Redis, MinIO, mock SATUSEHAT).
- [ ] `make smoke` passes.
- [ ] `make demo` exits 0 and every claim prints `[ok]`.
- [ ] `make retention` runs and is idempotent.
- [ ] `make restore-drill TENANT=acme` matches column-for-column.
- [ ] Encryption rotation drill: `make rewrap-secrets OLD_KEY=…` followed by a
      successful integration test in `/app/integrasi`.

## 2. Documentation

- [ ] `README.md` is under 220 lines, disclaimer above the first screenshot.
- [ ] `README.en.md` matches `README.md` in structure and claims.
- [ ] `docs/api.md` regenerated from OpenAPI.
- [ ] `docs/runbook.md`, `docs/quickstart.md`, `docs/satusehat.md`,
      `docs/design-review.md` reviewed.
- [ ] `docs/09-readme-and-demo.md` inventory matches the committed images.
- [ ] No secret, presigned URL, token, or non-`@example.com` address appears in
      docs or screenshots.

## 3. Screenshots and social preview

- [ ] `make screenshots` regenerates all nine images from seeded demo data.
- [ ] Every image is ≤ 250 KB, PNG, with meaningful alt text in the README.
- [ ] `docs/screenshots/cover.png` is exactly 1280×640 and ≤ 1 MB.
- [ ] The cover is uploaded manually under **Settings → Social preview** on
      GitHub. This is not read from the repository.

## 4. Version and announcement

- [ ] `version` in `backend/app/config.py`, `backend/pyproject.toml`,
      `frontend/package.json`, and the API title say `0.1.0`.
- [ ] `CHANGELOG.md` has an entry for `v0.1.0`.
- [ ] Tag: `git tag -a v0.1.0 -m "Sehat Bridge v0.1.0" && git push origin v0.1.0`.
- [ ] GitHub release points at the tag, includes the demo output, and links the
      disclaimer.
- [ ] Record the release date in `docs/00-handoff.md`.

## 5. Post-release smoke

```bash
make up
make health
make demo
open http://localhost:8080
open http://localhost:8080/ops/masuk
```

Sign in as `owner-acme@example.com` (faskes) and `ops@sehatbridge.dev` (operator)
with `demo-password-123`. Confirm the mobile layout at 390px and the block page
for a suspended tenant.