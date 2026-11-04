# Screenshots

Every image is generated from the running UI by `make screenshots`
(`tools/screenshots/capture.py`, Playwright). Do not hand-edit them.

The harness seeds deterministic rows into the `acme` tenant, logs in through
`/masuk` and `/ops/masuk`, and captures the nine images listed in
`docs/09-readme-and-demo.md`. Regenerate after a UI change:

```bash
make screenshots
make screenshots ARGS="--only beranda,dasbor"
```

`cover.png` is the 1280×640 social preview. Upload it manually under
**Settings → Social preview** on GitHub; the repository copy is a source asset,
not something GitHub reads automatically.