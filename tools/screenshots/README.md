# Screenshot harness

`capture.py` drives the real stack with Playwright (Python sync API). It seeds
deterministic file/job rows into the `acme` tenant, captures the nine images
from `docs/09-readme-and-demo.md`, and writes them to `docs/screenshots/`.

```bash
make screenshots
make screenshots ARGS="--only beranda,dasbor"
make screenshots ARGS="--no-seed"        # capture against existing rows
```

Requirements:

- a running stack at <http://localhost:8080>, seeded with `make seed`
- `uv run --with playwright playwright install chromium` once per machine

The harness fails if the UI is missing a sampled element, so a broken login or
renamed label is caught before images are committed. Images are captured at
2× device scale (3× on mobile), with reduced motion and hidden scrollbars.