from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# The original seven-step red CRT palette remains available as the default style.
# It is data, not a dependency on the application where the filter originated.
DEFAULT_PALETTE = [
    "#080303",
    "#230606",
    "#4a0e0c",
    "#942419",
    "#da4328",
    "#ff7648",
    "#ffc4a3",
]


class FilterSettings(BaseModel):
    """Every visible filter control lives here and is validated in one place."""

    contrast: float = Field(default=1.35, ge=0.1, le=5.0)
    brightness: float = Field(default=1.0, ge=0.1, le=3.0)
    gamma: float = Field(default=1.0, ge=0.2, le=3.0)
    dithering: bool = True
    scanline_opacity: float = Field(default=0.12, ge=0.0, le=1.0)
    scanline_spacing: int = Field(default=3, ge=2, le=20)
    scanline_width: int = Field(default=1, ge=1, le=10)
    vignette_strength: float = Field(default=0.18, ge=0.0, le=1.0)
    palette: list[str] = Field(default_factory=lambda: DEFAULT_PALETTE.copy())
    output_format: Literal["png", "jpeg", "webp"] = "webp"
    quality: int = Field(default=92, ge=1, le=100)

    @field_validator("palette")
    @classmethod
    def validate_palette(cls, colors: list[str]) -> list[str]:
        if not 2 <= len(colors) <= 16:
            raise ValueError("palette must contain between 2 and 16 colors")
        normalized: list[str] = []
        for color in colors:
            value = color.strip().lower()
            if not re.fullmatch(r"#[0-9a-f]{6}", value):
                raise ValueError("palette colors must use #rrggbb")
            normalized.append(value)
        return normalized


DEFAULT_PRESET = {
    "name": "Red CRT",
    "settings": FilterSettings().model_dump(),
}
