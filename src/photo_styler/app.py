from __future__ import annotations

import asyncio
import os
import re
import unicodedata
import webbrowser
from argparse import ArgumentParser
from collections.abc import AsyncGenerator
from pathlib import Path, PurePosixPath
from threading import Timer

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from . import __version__
from .filter_config import FilterSettings
from .filter_pipeline import ImageLimitError, render_bytes
from .presets import Preset, list_presets, save_preset

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_SETTINGS_BYTES = 16 * 1024
MAX_RENDER_BODY_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
ALLOWED_HOSTS = LOCAL_HOSTS | {
    host.strip().lower()
    for host in os.getenv("PHOTO_STYLER_ALLOWED_HOSTS", "").split(",")
    if host.strip()
}
HOST_PATTERN = re.compile(r"(\[[0-9a-f:]+\]|[a-z0-9.-]+)(?::[0-9]+)?")
RENDER_LOCK = asyncio.Lock()

app = FastAPI(title="Photo Styler", version=__version__, docs_url=None, redoc_url=None)


@app.middleware("http")
async def protect_local_app(request: Request, call_next) -> Response:
    authority = request.headers.get("host", "").lower()
    host_match = HOST_PATTERN.fullmatch(authority)
    origin = request.headers.get("origin")
    if not host_match or host_match[1] not in ALLOWED_HOSTS:
        response = JSONResponse({"detail": "Host is not allowed"}, status_code=400)
    elif request.method == "POST" and (
        request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}
        or (origin is not None and origin.lower() != f"{request.url.scheme}://{authority}")
    ):
        response = JSONResponse({"detail": "Cross-origin writes are disabled"}, status_code=403)
    else:
        response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' blob:; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


async def _bounded_body(request: Request, limit: int) -> AsyncGenerator[bytes, None]:
    length = request.headers.get("content-length")
    if length is not None:
        try:
            declared = int(length)
        except ValueError as exc:
            raise HTTPException(400, "Invalid request length") from exc
        if declared < 0:
            raise HTTPException(400, "Invalid request length")
        if declared > limit:
            raise HTTPException(413, "Request exceeds the size limit")

    total = 0
    try:
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                raise HTTPException(413, "Request exceeds the size limit")
            yield chunk
    except ClientDisconnect as exc:
        raise HTTPException(400, "The upload was interrupted") from exc


def _safe_export_name(filename: str | None, extension: str) -> str:
    stem = PurePosixPath((filename or "").replace("\\", "/")).stem
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", ascii_stem)[:80].strip("-_")
    return f"{safe_stem or 'image'}-styled.{extension}"


@app.get("/api/presets", response_model=list[Preset])
def get_presets() -> list[Preset]:
    try:
        return list_presets()
    except OSError as exc:
        raise HTTPException(500, "The preset directory is unavailable") from exc


@app.post("/api/presets", response_model=Preset)
async def create_preset(request: Request) -> Preset:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        raise HTTPException(415, "Presets require application/json")
    try:
        async with asyncio.timeout(30):
            raw = b"".join([chunk async for chunk in _bounded_body(request, MAX_SETTINGS_BYTES)])
    except TimeoutError as exc:
        raise HTTPException(408, "The upload timed out") from exc
    try:
        preset = Preset.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid preset name or settings") from exc
    try:
        return await run_in_threadpool(save_preset, preset)
    except OSError as exc:
        raise HTTPException(500, "The preset could not be saved") from exc


async def _read_render_form(request: Request) -> tuple[bytes, str | None, FilterSettings]:
    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "multipart/form-data":
        raise HTTPException(415, "Rendering requires multipart/form-data")
    parser = MultiPartParser(
        request.headers,
        _bounded_body(request, MAX_RENDER_BODY_BYTES),
        max_files=1,
        max_fields=1,
        max_part_size=MAX_SETTINGS_BYTES,
    )
    try:
        async with asyncio.timeout(30):
            form = await parser.parse()
    except TimeoutError as exc:
        raise HTTPException(408, "The upload timed out") from exc
    except (MultiPartException, MultipartParseError, ValueError) as exc:
        raise HTTPException(400, "Invalid image form") from exc

    try:
        image, raw_settings = form.get("image"), form.get("settings")
        if not isinstance(image, UploadFile) or not isinstance(raw_settings, str):
            raise HTTPException(422, "Provide one image and its filter settings")
        if not image.size:
            raise HTTPException(400, "The uploaded file is empty")
        if image.size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Photo Styler accepts images up to 32 MiB")
        try:
            settings = FilterSettings.model_validate_json(raw_settings)
        except ValidationError as exc:
            raise HTTPException(422, "Invalid filter settings") from exc
        return await image.read(), image.filename, settings
    finally:
        await form.close()


@app.post("/api/render/{mode}")
async def render(mode: str, request: Request) -> Response:
    if mode not in {"preview", "export"}:
        raise HTTPException(404, "Unknown render mode")
    if RENDER_LOCK.locked():
        raise HTTPException(429, "An image is already being processed")
    async with RENDER_LOCK:
        data, filename, settings = await _read_render_form(request)
        try:
            rendered, media_type, extension = await run_in_threadpool(
                render_bytes, data, settings, preview_max_size=1200 if mode == "preview" else None
            )
        except (ImageLimitError, Image.DecompressionBombError) as exc:
            raise HTTPException(413, "Image exceeds 16 megapixels or 8192 pixels per side") from exc
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError, RuntimeError) as exc:
            raise HTTPException(415, "The selected image could not be decoded or rendered") from exc
    headers = {}
    if mode == "export":
        headers["Content-Disposition"] = (
            f'attachment; filename="{_safe_export_name(filename, extension)}"'
        )
    return Response(rendered, media_type=media_type, headers=headers)


app.mount("/", StaticFiles(directory=STATIC_DIRECTORY, html=True), name="static")


def run() -> None:
    parser = ArgumentParser(description="Run Photo Styler locally.")
    parser.add_argument("--host", default=os.getenv("PHOTO_STYLER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=os.getenv("PHOTO_STYLER_PORT", "8765"))
    parser.add_argument("--open-browser", action="store_true", help="Open the UI in a browser")
    args = parser.parse_args()
    if args.open_browser:
        browser_host = {"0.0.0.0": "127.0.0.1", "::": "[::1]", "::1": "[::1]"}.get(
            args.host, args.host
        )
        Timer(0.8, webbrowser.open, args=(f"http://{browser_host}:{args.port}",)).start()
    uvicorn.run(app, host=args.host, port=args.port, proxy_headers=False, limit_concurrency=16)
