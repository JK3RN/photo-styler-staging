"""Generate the original, synthetic Photo Styler demo scene and its README banner."""

from __future__ import annotations

from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageFont

DIRECTORY = Path(__file__).resolve().parent
FONT = Path("/usr/share/fonts/liberation/LiberationMono-Regular.ttf")
if not FONT.exists():
    FONT = Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf")


def scene() -> Image.Image:
    width, height = 1440, 900
    random = Random(492)
    image = Image.new("RGB", (width, height))
    pixels = []
    for y in range(height):
        horizon = max(0.0, 1 - abs(y - 495) / 520)
        for x in range(width):
            glow = max(0.0, 1 - ((x - 960) / 690) ** 2) * horizon**3
            noise = random.randrange(-3, 4)
            pixels.append(
                (
                    int(10 + 142 * glow + 11 * horizon) + noise,
                    int(17 + 71 * glow + 25 * horizon) + noise,
                    int(36 + 48 * glow + 49 * horizon) + noise,
                )
            )
    image.putdata(pixels)
    draw = ImageDraw.Draw(image)
    for _ in range(150):
        x, y = random.randrange(width), random.randrange(460)
        value = random.randrange(79, 188)
        draw.point((x, y), fill=(value, value, min(255, value + 20)))
    draw.ellipse((813, 173, 1107, 467), fill="#ffce9b")
    for y in range(180, 460):
        half_span = int((147**2 - (y - 320) ** 2) ** 0.5)
        draw.line((960 - half_span, y, 960 + half_span, y), fill=(255, 211 - (y - 180) // 3, 159))
    draw.polygon(
        [
            (0, 548),
            (185, 362),
            (268, 423),
            (425, 315),
            (571, 472),
            (723, 378),
            (848, 515),
            (1059, 375),
            (1232, 455),
            (1440, 338),
            (1440, 699),
            (0, 699),
        ],
        fill="#53627a",
    )
    draw.polygon(
        [
            (0, 595),
            (223, 469),
            (360, 558),
            (481, 464),
            (701, 592),
            (911, 490),
            (1152, 610),
            (1353, 470),
            (1440, 522),
            (1440, 900),
            (0, 900),
        ],
        fill="#232d43",
    )
    draw.polygon(
        [
            (0, 648),
            (220, 621),
            (387, 649),
            (594, 591),
            (886, 668),
            (1134, 642),
            (1440, 720),
            (1440, 900),
            (0, 900),
        ],
        fill="#111827",
    )
    for y in range(674, 900, 8):
        t = (y - 674) / 226
        draw.line((0, y, width, y), fill=(22 + int(13 * t), 34 + int(18 * t), 52 + int(20 * t)))
    for x in range(-450, 1900, 160):
        draw.line((708, 628, x, 900), fill="#435269", width=2)
    draw.polygon([(616, 900), (699, 628), (724, 628), (952, 900)], fill="#687281")
    draw.line((716, 633, 784, 900), fill="#e5b467", width=4)
    for x, y in [(160, 663), (1160, 704), (371, 714)]:
        draw.polygon([(x - 31, y), (x, y - 124), (x + 31, y)], fill="#18273a")
        draw.line((x, y - 124, x, y), fill="#99a6b8", width=2)
        draw.ellipse((x - 4, y - 128, x + 4, y - 120), fill="#f1ce88")
    return image


def banner(source: Image.Image) -> Image.Image:
    image = Image.new("RGB", (1440, 410), "#0a1010")
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 1421, 391), outline="#31413e", width=2)
    draw.line((46, 68, 766, 68), fill="#00ff66", width=2)
    draw.line((46, 333, 766, 333), fill="#31413e", width=2)

    def font(size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(str(FONT), size)

    draw.text((46, 34), "RETROTOOLS / IMAGE PROCESSING", fill="#00ff66", font=font(22))
    draw.text((44, 113), "Photo Styler", fill="#f0f5ee", font=font(84))
    draw.text((47, 243), "PALETTES / DITHERING / CRT", fill="#ffcc00", font=font(27))
    draw.text((47, 348), "LOCAL IMAGE LAB", fill="#98aeaa", font=font(20))

    preview = source.resize((568, 355), Image.Resampling.LANCZOS).crop((0, 14, 568, 339))
    image.paste(preview, (813, 42))
    draw.rectangle((812, 41, 1381, 367), outline="#566a60", width=1)
    return image


if __name__ == "__main__":
    original = scene()
    original.save(DIRECTORY / "signal-valley.png", optimize=True)
    banner(original).save(DIRECTORY / "banner.png", optimize=True)
