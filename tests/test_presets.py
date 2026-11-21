from photo_styler.filter_config import DEFAULT_PRESET, FilterSettings
from photo_styler.presets import Preset, list_presets, save_preset


def test_default_preset_is_a_valid_red_crt_preset() -> None:
    preset = Preset.model_validate(DEFAULT_PRESET)

    assert preset.name == "Red CRT"
    assert preset.settings == FilterSettings()


def test_bundled_presets_include_red_and_dusk_cyan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PHOTO_STYLER_DATA_DIR", str(tmp_path))
    presets = {preset.name: preset for preset in list_presets()}

    assert {"Red CRT", "Dusk Cyan Artwork"}.issubset(presets)
    cyan = presets["Dusk Cyan Artwork"].settings
    assert cyan.contrast < 1
    assert cyan.brightness < 1
    assert cyan.vignette_strength > FilterSettings().vignette_strength
    assert cyan.palette[-1] == "#a5c7c9"


def test_saved_presets_use_the_configured_data_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PHOTO_STYLER_DATA_DIR", str(tmp_path))

    save_preset(Preset(name="My Style", settings=FilterSettings()))

    assert (tmp_path / "presets" / "my-style.json").is_file()
    assert "My Style" in {preset.name for preset in list_presets()}


def test_existing_invalid_files_do_not_hide_bundled_and_valid_presets(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_STYLER_DATA_DIR", str(tmp_path))
    preset = Preset(name="Kept", settings=FilterSettings())
    save_preset(preset)
    directory = tmp_path / "presets"
    (directory / "broken.json").write_text("{")
    (directory / "large.json").write_bytes(b" " * (16 * 1024 + 1))

    assert {item.name for item in list_presets()} >= {"Kept", "Red CRT"}


def test_preset_symlink_is_ignored_and_replaced_without_writing_target(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTO_STYLER_DATA_DIR", str(tmp_path / "data"))
    outside = tmp_path / "outside.json"
    outside.write_text(Preset(name="Outside", settings=FilterSettings()).model_dump_json())
    original = outside.read_bytes()
    directory = tmp_path / "data" / "presets"
    directory.mkdir(parents=True)
    existing = directory / "local-name.json"
    existing.symlink_to(outside)

    assert "Outside" not in {preset.name for preset in list_presets()}
    save_preset(Preset(name="Local Name", settings=FilterSettings()))

    assert not existing.is_symlink()
    assert outside.read_bytes() == original
    assert {path.name for path in directory.iterdir()} == {"local-name.json"}
