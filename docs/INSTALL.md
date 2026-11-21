# Install Photo Styler

## Native Linux

The supported target is Linux x86-64 with CPython 3.12–3.14. The locked installation uses uv 0.13.9 and PyPI. Allow roughly 512 MiB of available RAM for typical local use, with additional headroom for large images or concurrent browser use. The server can create an upload spool of up to about 32 MiB in the system temporary directory.

From the checkout:

```bash
uv sync --locked --no-dev --no-editable
uv run --no-sync photo-styler
```

The app also installs from the built wheel. To use the lock for its dependency set before installing that wheel:

```bash
uv sync --locked --no-dev --no-install-project
uv pip install --no-deps dist/photo_styler-0.1.0-py3-none-any.whl
uv run --no-sync photo-styler
```

For optional HEIC/HEIF import, run `uv sync --locked --no-dev --no-editable --extra heif` before starting. Browser file pickers may require selecting **All files** for a phone image whose MIME type is missing. Export remains PNG, JPEG, or WebP.

| Setting | Default |
| --- | --- |
| `--host` / `PHOTO_STYLER_HOST` | `127.0.0.1` |
| `--port` / `PHOTO_STYLER_PORT` | `8765` |
| `--open-browser` | Off. Open the local URL explicitly or pass the flag. |
| `PHOTO_STYLER_ALLOWED_HOSTS` | Adds comma-separated hostnames or IPs to the loopback host list. Omit ports. |
| `PHOTO_STYLER_DATA_DIR` | `${XDG_DATA_HOME:-$HOME/.local/share}/photo-styler` |

The server writes presets beneath `presets/` in the selected data directory. Preserve that directory to keep your presets. Existing valid preset JSON can be copied there. Preset names that normalize to the same filename replace the previous preset. Browser site data and downloaded exports are maintained separately.

Stop the process with `Ctrl+C`. To uninstall, remove the project’s `.venv` or remove the package from that project environment with `uv pip uninstall photo-styler`. Remove the data directory and browser site data only if you want to discard your settings. Downloads stay under your browser’s control.

## Docker

Use Docker Engine 28 or later. Build from the checkout with network access to Docker Hub and PyPI:

```bash
docker build --tag photo-styler:0.1.0 .
docker run --rm --read-only --tmpfs /tmp --name photo-styler \
  -p 127.0.0.1:8765:8765 -v photo-styler-data:/data photo-styler:0.1.0
```

Open [the local app](http://127.0.0.1:8765). The process runs as UID and GID 10001 and listens on `0.0.0.0:8765` **inside the container**. The example publishes the port on the Docker host’s IPv4 loopback. Omitting `127.0.0.1:` publishes on all host interfaces. Other containers on the same Docker network may be able to reach the service. Docker versions before 28 have a documented limitation that can make loopback-published ports reachable from the same layer-2 segment. See [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/).

The image uses a digest-pinned Debian Bookworm Python base and the locked Python dependency set. HEIF is available through the native installation. The named volume stores presets. The optional read-only root filesystem in the example leaves `/data` and the temporary filesystem writable. The temporary filesystem consumes host memory as it fills. A named volume with existing files must be writable by container UID 10001.

Stop the container with `Ctrl+C` or `docker stop photo-styler`. Because the command uses `--rm`, Docker removes the stopped container. Remove the image with `docker image rm photo-styler:0.1.0`. After backing up any presets you wish to keep, remove the named volume with `docker volume rm photo-styler-data`.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Port is already in use | Start the native app with `--port 8766`, or map `127.0.0.1:8766:8765` in Docker, then use port 8766 in the browser. |
| Host rejected | Use the displayed loopback URL. An intentional non-loopback deployment requires an explicit bind address and a matching `PHOTO_STYLER_ALLOWED_HOSTS` entry. |
| Image rejected | Check the format and limits. Download or convert a single-frame PNG, JPEG or WebP locally, or install the HEIF extra if needed. |
| Presets cannot be saved | Check permissions on the selected data directory and the container volume. Invalid local preset files are skipped with a server-log warning. |
| Locked install fails | Check the uv version, CPython version, available platform wheels, and access to PyPI. Use the committed lockfile from the same checkout. |
