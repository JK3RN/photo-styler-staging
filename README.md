![RetroTools Photo Styler banner](docs/media/banner.png)

# Photo Styler

A local web app for palette-based image styling. Import a photo, tune its tones and CRT effects, and export at full resolution. A Python process on your machine renders the image and serves the browser interface.

## Try it

Use Linux with Python 3.12, 3.13, or 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.9. From the project checkout:

```bash
uv sync --locked --no-dev --no-editable
uv run --no-sync photo-styler
```

Open [Photo Styler on loopback](http://127.0.0.1:8765). Import an image with **Bild auswählen**, select a preset and click **Laden**. Use **Vollauflösung speichern** to export. Stop the server with `Ctrl+C`.

| Capability | Release scope |
| --- | --- |
| Input | Single-frame JPEG, PNG and WebP. Optional HEIC/HEIF decoder. |
| Styling | Contrast, brightness, gamma, editable palette colors, Floyd–Steinberg dithering, scanlines and vignette |
| Presets | Red CRT, Dusk Cyan Artwork and locally saved presets |
| Output | Preview up to 1200 px on its longest side. Full-resolution PNG, JPEG or WebP export within input limits. |

## Showcase

Three photographs, processed in the running app. Open a screenshot to see the controls at full size.

| Original | In Photo Styler |
| --- | --- |
| **Chicago at night**<br>[<img src="docs/media/showcase/chicago-original.jpg" width="230" alt="Aerial photograph of Chicago and Lake Michigan at night">](docs/media/showcase/chicago-original.jpg) | [![Photo Styler applying a green CRT palette to the Chicago street grid](docs/media/showcase/chicago-app.webp)](docs/media/showcase/chicago-app.webp)<br>**Phosphor Grid** · green palette, Floyd–Steinberg dithering and visible scanlines |
| **Death Valley dunes**<br>[<img src="docs/media/showcase/death-valley-original.jpg" width="230" alt="Sunlit ridges and shadows in the Death Valley dunes">](docs/media/showcase/death-valley-original.jpg) | [![Photo Styler rendering the dunes in cool blue shades with darker edges](docs/media/showcase/death-valley-app.webp)](docs/media/showcase/death-valley-app.webp)<br>**Blue Hour** · cool blues and a vignette that draws the eye to the ridges |
| **Hoover Dam**<br>[<img src="docs/media/showcase/hoover-dam-original.jpg" width="230" alt="Black-and-white archival photograph of the upstream face of Hoover Dam">](docs/media/showcase/hoover-dam-original.jpg) | [![Photo Styler rendering the dam in a five-color sulfur and plum palette](docs/media/showcase/hoover-dam-app.webp)](docs/media/showcase/hoover-dam-app.webp)<br>**Sulfur Print** · five colors and hard tonal steps with dithering off |

These looks use custom settings. See the [image credits](THIRD_PARTY_NOTICES.md#showcase-photographs) or try the synthetic [Signal Valley example](docs/media/signal-valley.png) with the built-in **Red CRT** preset ([matching export](docs/media/signal-valley-red-crt.png)).

## How it works

The browser serves as the file picker and editor. It sends the selected image and settings over local HTTP to FastAPI. Pillow decodes the image, applies its EXIF orientation, converts tone to palette colors, and renders the CRT effects. The browser receives an image preview or download. The Python pipeline in `photo_styler.filter_pipeline` also accepts image bytes or a Pillow image directly.

The server binds to `127.0.0.1` by default. It accepts images up to 32 MiB, 16 megapixels and 8192 pixels per side, and processes one render at a time. Uploads may spool to a temporary file during parsing. The server saves preset JSON on request. The browser retains the current filter settings in local storage and manages export downloads. Exported images omit source EXIF, XMP and embedded color profiles. See the [security and privacy details](SECURITY.md).

## Project information

- [Installation, optional HEIF, Docker and troubleshooting](docs/INSTALL.md)
- [Test and build commands](docs/QA.md)
- [Changelog](CHANGELOG.md) and [release notes draft](docs/RELEASE-NOTES.md)
- [MIT license](LICENSE) and [third-party notices and demo provenance](THIRD_PARTY_NOTICES.md)
