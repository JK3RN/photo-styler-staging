import json
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import photo_styler.app as application
from photo_styler.filter_config import FilterSettings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_STYLER_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    with TestClient(application.app, base_url="http://127.0.0.1:8765") as client:
        yield client


def make_image(image_format="PNG", size=(1600, 900)):
    buffer = BytesIO()
    Image.new("RGB", size, "white").save(buffer, image_format)
    return buffer.getvalue()


def render(client, data, *, mode="export", filename="sample.png", settings="{}"):
    return client.post(
        f"/api/render/{mode}",
        files={"image": (filename, data)},
        data={"settings": settings},
    )


def test_static_browser_entrypoint_is_present(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "PHOTO STYLER" in response.text
    assert "TRAVEL GRID" not in response.text
    assert "/app.js" in response.text
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/app.js").status_code == 200
    assert client.get("/favicon.png").headers["Content-Type"] == "image/png"


@pytest.mark.parametrize(
    ("source_format", "output_format", "extension", "pillow_format"),
    [
        ("PNG", "png", "png", "PNG"),
        ("JPEG", "jpeg", "jpg", "JPEG"),
        ("WEBP", "webp", "webp", "WEBP"),
    ],
)
def test_preview_and_repeated_full_resolution_exports(
    client, tmp_path, source_format, output_format, extension, pillow_format
):
    source = make_image(source_format)
    settings = FilterSettings(output_format=output_format).model_dump_json()
    preview = render(client, source, mode="preview", settings=settings)
    assert preview.status_code == 200
    assert "Content-Disposition" not in preview.headers
    with Image.open(BytesIO(preview.content)) as image:
        assert image.size == (1200, 675)
    for _ in range(2):
        response = render(client, source, settings=settings)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == f"image/{output_format}"
        assert response.headers["Cache-Control"] == "no-store"
        assert (
            response.headers["Content-Disposition"]
            == f'attachment; filename="sample-styled.{extension}"'
        )
        with Image.open(BytesIO(response.content)) as exported:
            assert exported.size == (1600, 900)
            assert exported.format == pillow_format
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    ("data", "settings", "status"),
    [
        (b"", "{}", 400),
        (b"invalid image", "{}", 415),
        (make_image()[:80], "{}", 415),
        (make_image("GIF"), "{}", 415),
        (make_image(size=(9000, 1)), "{}", 413),
        (make_image(size=(4100, 4000)), "{}", 413),
        (make_image(), "invalid JSON", 422),
        (make_image(), '{"output_format":"gif"}', 422),
        (make_image(), '{"palette":["#+fffff","#000000"]}', 422),
        (make_image(), " " * (16 * 1024 + 1), 400),
    ],
)
def test_rejects_invalid_images_and_settings(client, data, settings, status):
    assert render(client, data, settings=settings).status_code == status


def test_safe_download_filename(client):
    source = make_image(size=(8, 8))
    response = render(client, source, filename="Übung 🖼️.png", settings='{"output_format":"png"}')
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == 'attachment; filename="Ubung-styled.png"'
    assert application._safe_export_name("subfolder/sample.png", "png") == "sample-styled.png"
    assert application._safe_export_name("🖼️.png", "png") == "image-styled.png"


def test_size_limits_include_streams_without_content_length(client, monkeypatch):
    monkeypatch.setattr(application, "MAX_RENDER_BODY_BYTES", 512)
    payload = make_image(size=(80, 80))
    assert render(client, payload * 10).status_code == 413

    def chunks():
        yield b"x" * 256
        yield b"x" * 257

    response = client.post(
        "/api/presets", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    monkeypatch.setattr(application, "MAX_SETTINGS_BYTES", 512)
    response = client.post(
        "/api/presets", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


def test_limits_file_size_separately_from_form_size(client, monkeypatch):
    monkeypatch.setattr(application, "MAX_UPLOAD_BYTES", 100)
    assert render(client, make_image()).status_code == 413


def test_rejects_unexpected_host_and_cross_origin_post(client):
    assert client.get("/", headers={"Host": "example.test"}).status_code == 400
    assert client.get("/", headers={"Host": "[::1]:8765"}).status_code == 200
    payload = {"name": "Local Example", "settings": {}}
    assert (
        client.post(
            "/api/presets", json=payload, headers={"Origin": "https://example.test"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/presets", json=payload, headers={"Origin": "http://127.0.0.1:8765"}
        ).status_code
        == 200
    )


def test_presets_round_trip_and_reject_invalid_values(client):
    preset = {"name": "QA Cyan", "settings": {"palette": ["#112233", "#aabbcc"]}}
    response = client.post(
        "/api/presets", content=json.dumps(preset), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json() in client.get("/api/presets").json()
    assert client.post("/api/presets", json={"name": " ", "settings": {}}).status_code == 422
    assert client.post("/api/presets", data={"name": "QA"}).status_code == 415


def test_second_render_is_rejected_while_first_render_is_active(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    source = make_image(size=(64, 32))
    started = Event()
    release = Event()
    original_render = application.render_bytes

    def blocked_render(*args, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        return original_render(*args, **kwargs)

    monkeypatch.setattr(application, "render_bytes", blocked_render)
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(render, client, source)
        try:
            assert started.wait(timeout=5)
            assert client.get("/").status_code == 200
            assert render(client, source).status_code == 429
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
    assert render(client, source).status_code == 200


def test_animated_png_is_rejected(client):
    source = BytesIO()
    Image.new("RGB", (16, 16), "white").save(
        source, "PNG", save_all=True, append_images=[Image.new("RGB", (16, 16), "black")]
    )
    assert render(client, source.getvalue()).status_code == 415
