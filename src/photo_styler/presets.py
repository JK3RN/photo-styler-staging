from __future__ import annotations

import logging
import os
import re
import stat
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, Field, field_validator

from .filter_config import DEFAULT_PRESET, FilterSettings

LOGGER = logging.getLogger(__name__)
MAX_PRESET_BYTES = 16 * 1024


class Preset(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    settings: FilterSettings

    @field_validator("name")
    @classmethod
    def validate_name(cls, name: str) -> str:
        name = name.strip()
        if not name or not name.isprintable():
            raise ValueError("Use a non-empty printable name")
        return name


def preset_directory() -> Path:
    configured = os.getenv("PHOTO_STYLER_DATA_DIR")
    if configured:
        return Path(configured).expanduser() / "presets"
    data_home = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return data_home / "photo-styler" / "presets"


def bundled_preset_directory() -> Path:
    return Path(__file__).resolve().parent / "bundled_presets"


def _read_preset(path: Path) -> Preset:
    def open_regular(filename: str, flags: int) -> int:
        fd = os.open(filename, flags | os.O_NOFOLLOW | os.O_NONBLOCK)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise OSError("Expected a regular preset file")
        return fd

    with open(path, "rb", opener=open_regular) as handle:
        data = handle.read(MAX_PRESET_BYTES + 1)
    if len(data) > MAX_PRESET_BYTES:
        raise ValueError("Preset is too large")
    return Preset.model_validate_json(data)


def list_presets() -> list[Preset]:
    presets = {DEFAULT_PRESET["name"]: Preset.model_validate(DEFAULT_PRESET)}
    for path in sorted(bundled_preset_directory().glob("*.json")):
        preset = _read_preset(path)
        presets[preset.name] = preset
    directory = preset_directory()
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise OSError("Expected a preset directory")
    for path in sorted(directory.glob("*.json")):
        try:
            preset = _read_preset(path)
        except (OSError, ValueError):
            LOGGER.warning("Skipping invalid local preset")
            continue
        presets[preset.name] = preset
    return sorted(presets.values(), key=lambda preset: preset.name.casefold())


def save_preset(preset: Preset) -> Preset:
    directory = preset_directory()
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    if directory.is_symlink():
        raise OSError("Expected a preset directory")
    slug = re.sub(r"[^a-z0-9]+", "-", preset.name.lower()).strip("-") or "preset"
    target = directory / f"{slug}.json"
    with NamedTemporaryFile(dir=directory, mode="w", encoding="utf-8", delete=False) as handle:
        pending = Path(handle.name)
        try:
            handle.write(preset.model_dump_json(indent=2) + "\n")
            handle.close()
            pending.replace(target)
        finally:
            pending.unlink(missing_ok=True)
    return preset
