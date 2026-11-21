# Release verification

## Reproduce the build and tests

From the checkout, use uv 0.13.9 and run:

```bash
for version in 3.12 3.13 3.14; do
  uv sync --locked --extra dev --python "$version"
  uv run --no-sync ruff check .
  uv run --no-sync pytest -ra
  SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)" \
    uv run --no-sync python -m build --no-isolation
done
uv sync --locked --extra dev --extra heif --python 3.13
uv run --no-sync pytest -ra
node --check docs/media/browser-smoke.mjs
```

The test suite covers the HTTP routes, PNG/JPEG/WebP, invalid and animated images, pixel and byte caps, repeated and concurrent requests, same-origin checks, export names, preset symlinks and malformed presets, EXIF orientation, palette mapping, error diffusion and CRT effects. The HEIF test checks the optional decoder when installed and its absence otherwise.

Fresh native CLI and wheel installation are described in [INSTALL.md](INSTALL.md). To repeat the Chromium workflow with that wheel installed, use Chromium and Node.js 22 or later. Run from the project directory:

```bash
smoke=$(mktemp -d)
PHOTO_STYLER_DATA_DIR="$smoke/data" TMPDIR="$smoke" photo-styler --port 18765
```

In a second terminal, use the same value for `smoke` and start Chromium with an isolated profile:

```bash
chromium --headless --disable-background-networking --disable-component-update \
  --no-first-run --no-default-browser-check --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=0 --user-data-dir="$smoke/profile" about:blank
```

In a third terminal with the same `smoke` value:

```bash
node docs/media/browser-smoke.mjs docs/media "$smoke/downloads" "$smoke/profile" \
  http://127.0.0.1:18765/
```

The script exercises the real UI, switches from Dusk Cyan Artwork to Red CRT, saves a full-resolution PNG to the isolated download directory, and checks that a saved preset survives reload. It captures the preview screen before testing edited colors, dither and scanlines. Check the exported dimensions of 1440 × 900 px, and close both processes after the test. Use [the CI workflow](../.github/workflows/ci.yml) to reproduce the Docker Engine smoke locally.

## Repeat dependency and repository scanning

```bash
uv export --quiet --locked --no-emit-project --extra heif \
  --format requirements.txt -o /tmp/photo-styler-runtime.txt
uv export --quiet --locked --no-emit-project --extra dev --extra heif \
  --format requirements.txt -o /tmp/photo-styler-dependencies.txt
pip-audit --disable-pip --require-hashes -r /tmp/photo-styler-runtime.txt
pip-audit --disable-pip --require-hashes -r /tmp/photo-styler-dependencies.txt
gitleaks git --log-opts=--all --redact --no-banner .
git fsck --full --no-reflogs
git ls-tree -r --name-only HEAD
```

The dependency audit covers versioned Python packages. Bundled native libraries and operating system packages require separate analysis before publishing a prebuilt container or vendored dependency bundle.

## Verification scope

The verified native platform is Linux x86-64 with CPython 3.12, 3.13 and 3.14. The Linux/amd64 Docker Engine job checks loopback-only port publishing, non-root execution, full-resolution export, and preset persistence across container replacement using a fresh named volume.
