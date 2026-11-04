# 09 — README, Screenshots & Demo

The README is the product's front door. It must prove three things in under 30
seconds of scrolling: **what this is**, **what it looks like**, and **that it
runs**.

## 1. README structure

Target ≤ 220 lines. Anything longer moves to `docs/`.

```
1.  Title + one-line description            (3 lines)
2.  Badges: CI, Python, Node, license        (1 line)
3.  Hero screenshot (marketing beranda)      (1 image)
4.  Disclaimer (not affiliated with Kemenkes)(2 lines)
5.  Why this exists / who it is for          (5 lines)
6.  Screenshots grid with captions           (8-9 images)
7.  Architecture diagram                     (1 diagram + 3 bullets)
8.  Quickstart (60 seconds, copy-paste)      (12 lines)
9.  What's inside (feature bullets, grouped) (15 lines)
10. API at a glance (endpoint table, link)   (10 lines)
11. SATUSEHAT: mock vs live, plainly stated  (8 lines)
12. Security model (the 5 claims that matter)(8 lines)
13. Project status + roadmap                 (6 lines)
14. Development (make targets, tests)        (10 lines)
15. Docs index + license                     (6 lines)
```

Rules:
- Every claim links to code, a test, or a doc. No unverifiable adjectives.
- Quickstart commands are pasted verbatim into CI, so they cannot rot.
- The disclaimer sits **above** the first screenshot's caption.
- Screenshots use relative paths (`docs/screenshots/…`) so forks render too.

## 2. Screenshot inventory

Captured from seeded demo data, Bahasa Indonesia, original marketing copy.

Every image is real UI. Marketing shots are the actual pages; app shots are the
actual app with seeded rows. No Figma, no composited mockups.

| File | Surface | Must show | Caption / alt text |
|---|---|---|---|
| `cover.png` | `/` hero | Product name, H1, CTA, product visual | Social preview (1280×640) |
| `01-beranda.png` | `/` | Hero + trust line + first module row | "Beranda: satu alur untuk berkas dan integrasi" |
| `02-solusi.png` | `/solusi` | Module cards with anchors | "Modul yang tersedia" |
| `03-integrasi.png` | `/integrasi` | Honest status chips (`Mode uji`, `Direncanakan`) | "Status integrasi apa adanya" |
| `04-dasbor.png` | `/app/dasbor` | Quota, file count, sync, attention list | "Dasbor fasilitas" |
| `05-berkas.png` | `/app/berkas` | One upload in progress, two ready | "Unggah langsung ke penyimpanan objek" |
| `06-integrasi-app.png` | `/app/integrasi` | `Mode uji` band + one failed job | "Integrasi SATUSEHAT (mode uji)" |
| `07-ops-tenant.png` | `/ops/tenant` | Two tenants, statuses, provision CTA | "Konsol operator platform" |
| `08-mobile-beranda.png` | `/` @390px | Mobile nav, readable hero, CTA | "Tata letak responsif" |

Not captured: error pages, empty states (unless used in docs), anything with a
secret, presigned URL, a non-`@example.com` address, or a real NIK.

## 3. Capture harness

```
tools/screenshots/
  capture.py            Playwright (Python, sync API)
  scenario.yaml         shots: route, actions, wait-for, viewport
  fixtures/             fictional logo, avatar
docs/screenshots/       committed PNGs (a deliverable, not a build artifact)
```

Rules that make images reproducible:

| Concern | Rule |
|---|---|
| Target | `http://localhost:8080` (Caddy), so paths, cookies, and redirects match production |
| Viewport | 1440×900, `deviceScaleFactor=2`, capture at 2x then export 1440px wide |
| Mobile | 390×844, `deviceScaleFactor=3` |
| Fonts | `next/font` files are bundled; CI image pins the same Chromium version |
| Animation | `reducedMotion: "reduce"` + `animations="disabled"` in `screenshot()` |
| Cursor | never captured |
| Scrollbars | hidden via injected CSS for the capture only |
| Timing | `wait_for_load_state("networkidle")` + explicit `data-testid` waits; never `sleep()` |
| Data | `make seed --demo` with fixed ids and relative timestamps |
| Clock | `APP_DEMO_CLOCK=2026-01-15T09:00:00+07:00` freezes "x minutes ago" strings |
| Auth | log in through `/masuk` once, reuse the session cookie across app shots |
| Secrets | harness fails if the DOM contains `client_secret`, `X-Amz-Signature`, or a token-like string |
| Locale | `id-ID` fixed |
| Export | PNG, `oxipng`/`pngquant`, ≤ 250 KB each |

```bash
make screenshots            # boot, seed, capture, optimise
make screenshots -- --only beranda,dasbor
make screenshots-check      # regenerate to temp dir, pixel-diff vs committed
```

`screenshots-check` is **not** in the required PR pipeline (slow, font-sensitive).
It runs weekly and before a release tag, opening a PR with regenerated images
rather than failing a feature branch.

## 3.1 Language versions

`README.md` is the Indonesian front door and stays the GitHub default.
`README.en.md` is a full English mirror for external reviewers and contributors.
Both start with a language switcher linking to the other file, and both must
stay within the same structure and ≤ 220 lines. When a claim changes in one
file, update the other in the same commit — no drift between languages.

## 4. README embedding

```markdown
![Beranda Sehat Bridge](docs/screenshots/01-beranda.png)

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/04-dasbor.png" alt="Dasbor fasilitas"><br><sub>Dasbor fasilitas</sub></td>
    <td width="50%"><img src="docs/screenshots/05-berkas.png" alt="Unggah berkas"><br><sub>Unggah langsung ke penyimpanan objek</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/screenshots/06-integrasi-app.png" alt="Integrasi SATUSEHAT mode uji"><br><sub>Integrasi SATUSEHAT (mode uji)</sub></td>
    <td width="50%"><img src="docs/screenshots/07-ops-tenant.png" alt="Konsol operator"><br><sub>Konsol operator platform</sub></td>
  </tr>
</table>
```

Constraints:
- Plain Markdown/HTML only — no external image hosts, no autoplay GIF.
- Every image has meaningful `alt` text; captions duplicate it in `<sub>` because
  the image is supporting, not the only content.
- Nothing wider than 1200px rendered, or GitHub blurs the text.
- Do not use a screenshot to convey information absent from text.

## 5. Social preview

`docs/screenshots/cover.png` at exactly **1280×640**, ≤ 1 MB: product name,
one-line pitch, disclaimer mark, cropped hero. GitHub does not read it from the
repo — upload manually under *Settings → Social preview*. Note the step in
`docs/release.md`.

## 6. Demo script (`scripts/demo.sh`)

Runs against a live stack and prints a pass/fail line per claim:

```
[ok] health: postgres, redis, minio
[ok] marketing: / returns 200, sitemap present
[ok] lead captured from demo form
[ok] tenant provisioned: klinik-sehat
[ok] tenant provisioned: lab-nusantara
[ok] shared identity can join both tenants
[ok] forged X-Tenant-ID rejected (403)
[ok] member cannot change roles (403)
[ok] last owner cannot be demoted (409)
[ok] file uploaded, completed, downloaded
[ok] oversize upload rejected by storage policy
[ok] satusehat mock: token issued
[ok] satusehat mock: organization synced (id=fhir-org-…)
[ok] satusehat mock: 500 retried then succeeded
[ok] satusehat mock: 4xx failed without retry
[ok] secret absent from logs and responses
```

Exits non-zero on the first failure, printing the failed response.

## 7. Docs set and what each answers

| Doc | Question it answers |
|---|---|
| `docs/quickstart.md` | "How do I run this in 60 seconds?" |
| `docs/api.md` | "How do I call it?" (generated from OpenAPI) |
| `docs/satusehat.md` | "What exactly is mocked, and what do I need to go live?" |
| `docs/runbook.md` | "It broke at 2am, what do I check?" |
| `docs/design-review.md` | "How does this differ from the source design doc, and why?" |
| `docs/release.md` | "What is the tag checklist?" (incl. social preview) |
| `docs/screenshots/` | "What does it look like?" |

## 8. Acceptance

- [ ] Quickstart block passes verbatim in a clean container
- [ ] All 9 images present, ≤ 250 KB each, alt text filled
- [ ] Every screenshot regenerable with `make screenshots` from a clean checkout
- [ ] No secret, presigned URL, or non-example email in any image
- [ ] Disclaimer above the fold and in the footer
- [ ] `make demo` output linked, not hand-written
- [ ] README renders on GitHub and stays under 220 lines
- [ ] Mobile screenshot proves the 390px layout