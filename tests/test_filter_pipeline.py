from io import BytesIO

from PIL import Image

from photo_styler.filter_config import FilterSettings
from photo_styler.filter_pipeline import render_bytes, style_image


def test_travel_grid_red_filter_preserves_full_size_and_uses_palette() -> None:
    source = Image.linear_gradient("L").resize((96, 48)).convert("RGB")
    settings = FilterSettings(dithering=False, scanline_opacity=0, vignette_strength=0)

    result = style_image(source, settings)

    assert result.size == source.size
    assert set(result.get_flattened_data()).issubset(
        {tuple(bytes.fromhex(color.removeprefix("#"))) for color in settings.palette}
    )


def test_preview_is_limited_but_export_keeps_original_dimensions() -> None:
    source = Image.new("RGB", (1600, 900), "white")
    buffer = BytesIO()
    source.save(buffer, "PNG")
    settings = FilterSettings(output_format="png", scanline_opacity=0, vignette_strength=0)

    preview, _, _ = render_bytes(buffer.getvalue(), settings, preview_max_size=400)
    exported, media_type, extension = render_bytes(buffer.getvalue(), settings)

    with Image.open(BytesIO(preview)) as preview_image:
        assert preview_image.size == (400, 225)
    with Image.open(BytesIO(exported)) as export_image:
        assert export_image.size == (1600, 900)
    assert (media_type, extension) == ("image/png", "png")


def test_dithering_distributes_two_palette_colors_in_a_flat_midgray_patch():
    source = Image.new("L", (64, 64), 120)
    settings = FilterSettings(
        palette=["#0d0d0d", "#f2f2f2"], contrast=1, scanline_opacity=0, vignette_strength=0
    )

    dithered = style_image(source, settings)
    solid = style_image(source, settings.model_copy(update={"dithering": False}))

    assert {color for _, color in dithered.getcolors()} == {(13, 13, 13), (242, 242, 242)}
    assert solid.getcolors() == [(64 * 64, (13, 13, 13))]


def test_crt_effects_darken_scanlines_and_corners():
    source = Image.new("RGB", (64, 64), "white")
    settings = FilterSettings(dithering=False, scanline_opacity=0.5, vignette_strength=0.8)

    styled = style_image(source, settings)

    assert styled.getpixel((32, 31))[0] < styled.getpixel((32, 32))[0]
    assert styled.getpixel((0, 0))[0] < styled.getpixel((32, 32))[0]
    assert source.getpixel((0, 0)) == (255, 255, 255)


def test_exif_orientation_is_applied_and_metadata_is_removed():
    image = Image.new("RGB", (30, 20), "white")
    exif = image.getexif()
    exif[274] = 6
    exif[315] = "Synthetic Test"
    source = BytesIO()
    image.save(source, "JPEG", exif=exif)

    result, _, _ = render_bytes(source.getvalue(), FilterSettings(output_format="png"))

    with Image.open(BytesIO(result)) as exported:
        assert exported.size == (20, 30)
        assert not exported.getexif()
        assert not ({"exif", "xmp", "icc_profile"} & exported.info.keys())


def test_heif_is_optional_and_decodes_a_generated_fixture_when_available():
    from importlib.util import find_spec

    import pytest
    from PIL import UnidentifiedImageError

    if find_spec("pillow_heif") is None:
        with pytest.raises(UnidentifiedImageError):
            render_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heicmif1", FilterSettings())
        return
    source = BytesIO()
    Image.new("RGB", (64, 48), "white").save(source, "HEIF")
    encoded, _, _ = render_bytes(source.getvalue(), FilterSettings(output_format="png"))
    with Image.open(BytesIO(encoded)) as image:
        assert image.size == (64, 48)
