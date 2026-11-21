from __future__ import annotations

from io import BytesIO
from warnings import catch_warnings, simplefilter

from PIL import Image, ImageDraw, ImageEnhance, ImageOps
from PIL.Image import DecompressionBombWarning

from .filter_config import FilterSettings

MAX_IMAGE_PIXELS = 16_000_000
MAX_IMAGE_SIDE = 8192
INPUT_FORMATS = ["JPEG", "PNG", "WEBP"]


class ImageLimitError(ValueError):
    pass


try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    INPUT_FORMATS.append("HEIF")
except (ImportError, RuntimeError):
    pass


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def _apply_gamma(luminance: Image.Image, gamma: float) -> Image.Image:
    if gamma == 1.0:
        return luminance
    lookup = [round(255 * ((value / 255) ** (1 / gamma))) for value in range(256)]
    return luminance.point(lookup)


def _palette_map(luminance: Image.Image, settings: FilterSettings) -> Image.Image:
    colors = [_hex_to_rgb(color) for color in settings.palette]
    if settings.dithering:
        # Pillow applies error diffusion when quantizing RGB against a fixed palette.
        levels = [round(index * 255 / (len(colors) - 1)) for index in range(len(colors))]
        grayscale = Image.new("P", (1, 1))
        grayscale.putpalette([level for level in levels for _ in range(3)])
        indexed = luminance.convert("RGB").quantize(
            palette=grayscale, dither=Image.Dither.FLOYDSTEINBERG
        )
    else:
        indices = [value * len(colors) // 256 for value in range(256)]
        indexed = luminance.point(indices).convert("P")
    indexed.putpalette([channel for color in colors for channel in color])
    return indexed.convert("RGB")


def _apply_scanlines(image: Image.Image, settings: FilterSettings) -> Image.Image:
    if settings.scanline_opacity <= 0:
        return image
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = round(255 * settings.scanline_opacity)
    for y in range(settings.scanline_width, image.height, settings.scanline_spacing):
        draw.line(
            (0, y, image.width, y),
            fill=(0, 0, 0, alpha),
            width=settings.scanline_width,
        )
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _apply_vignette(image: Image.Image, strength: float, darkest: str) -> Image.Image:
    if strength <= 0:
        return image
    # Pillow creates the radial mask in optimized native code; this remains usable
    # for full-resolution exports unlike a Python loop over every pixel.
    side = max(image.size)
    scale = 256 / side
    left = (side - image.width) * scale / 2
    top = (side - image.height) * scale / 2
    box = (left, top, 256 - left, 256 - top)
    mask = Image.radial_gradient("L").resize(image.size, Image.Resampling.BILINEAR, box)
    mask = mask.point(lambda value: round(value * strength))
    dark = Image.new("RGB", image.size, _hex_to_rgb(darkest))
    return Image.composite(dark, image, mask)


def style_image(
    source: Image.Image,
    settings: FilterSettings,
    *,
    preview_max_size: int | None = None,
) -> Image.Image:
    """Return a styled copy. The supplied source image is never modified."""

    if max(source.size) > MAX_IMAGE_SIDE or source.width * source.height > MAX_IMAGE_PIXELS:
        raise ImageLimitError("Image dimensions exceed Photo Styler's limit")
    if getattr(source, "is_animated", False):
        raise ValueError("Photo Styler accepts only single-frame images")
    image = ImageOps.exif_transpose(source).convert("RGB")
    if preview_max_size:
        image.thumbnail((preview_max_size, preview_max_size), Image.Resampling.LANCZOS)
    image = ImageEnhance.Contrast(image).enhance(settings.contrast)
    image = ImageEnhance.Brightness(image).enhance(settings.brightness)
    luminance = _apply_gamma(ImageOps.grayscale(image), settings.gamma)
    styled = _palette_map(luminance, settings)
    styled = _apply_scanlines(styled, settings)
    return _apply_vignette(styled, settings.vignette_strength, settings.palette[0])


def render_bytes(
    data: bytes,
    settings: FilterSettings,
    *,
    preview_max_size: int | None = None,
) -> tuple[bytes, str, str]:
    with catch_warnings():
        simplefilter("error", DecompressionBombWarning)
        try:
            source = Image.open(BytesIO(data), formats=INPUT_FORMATS)
        except DecompressionBombWarning as exc:
            raise ImageLimitError("Image dimensions exceed Photo Styler's limit") from exc
    with source:
        styled = style_image(source, settings, preview_max_size=preview_max_size)
        styled.info.clear()
        output = BytesIO()
        format_names = {"png": "PNG", "jpeg": "JPEG", "webp": "WEBP"}
        media_types = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}
        save_options = {}
        if settings.output_format in {"jpeg", "webp"}:
            save_options["quality"] = settings.quality
        if settings.output_format == "webp":
            save_options["method"] = 6
        styled.save(output, format=format_names[settings.output_format], **save_options)
    extension = "jpg" if settings.output_format == "jpeg" else settings.output_format
    return output.getvalue(), media_types[settings.output_format], extension
