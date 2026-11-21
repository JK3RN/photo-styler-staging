# Third-party notices

Photo Styler source, project-generated media and its Python package are distributed under the [MIT license](LICENSE). The wheel contains Photo Styler code, browser assets and the bundled preset JSON. Dependency packages are fetched separately from PyPI. Their installed distributions provide their license and copyright notices.

## Python dependencies

The exact versions and artifact hashes are in [uv.lock](uv.lock). This inventory groups the Python installation by licenses reported in the locked packages' metadata and notices.

| Scope | Packages and licenses |
| --- | --- |
| Runtime, MIT | annotated-doc, annotated-types, anyio, FastAPI, h11, Pydantic, pydantic-core, typing-inspection |
| Runtime, BSD-3-Clause | Click, idna, Starlette, Uvicorn |
| Runtime, Apache-2.0 | opentelemetry-api, python-multipart |
| Runtime, other | Pillow (MIT-CMU), typing-extensions (PSF-2.0) |
| Optional HEIF | pillow-heif source (BSD-3-Clause). Its binary-wheel notices identify GPLv2 terms and bundled libheif (LGPLv3), libde265 (LGPLv3) and x265 (GPLv2). |
| Build and test | build, hatchling, iniconfig, pluggy, pyproject-hooks, pytest, Ruff, tomlkit and truststore (MIT), HTTPX2 and HTTPCore2 (BSD-3-Clause), Pygments (BSD-2-Clause), packaging (Apache-2.0 OR BSD-2-Clause), pathspec (MPL-2.0), trove-classifiers (Apache-2.0) |

Pillow’s wheels include native libraries for formats and rendering, including libjpeg-turbo, libpng and libwebp. Consult the [Pillow external-library inventory](https://pillow.readthedocs.io/en/stable/installation/building-from-source.html#external-libraries) and the wheel's installed notices. The HEIF extra also installs `pillow_heif-*.dist-info/licenses/LICENSES_bundled.txt` with library source links. Docker builds use the upstream Debian Bookworm Python image and the default Python dependencies. The proposed release assets are the project source and Python package artifacts. Before distributing a prebuilt container or a bundle of third-party wheels, review and satisfy the redistribution terms for the included OS packages and native libraries.

## Media and bundled presets

- `docs/media/signal-valley.png` is a generated landscape. [The generator](docs/media/generate.py) uses seeded noise and drawn geometry. It uses no photograph, external texture or location data.
- `docs/media/signal-valley-red-crt.png` is the application's PNG export of that synthetic image. `docs/media/application.png` is a real Chromium capture made with the same image and bundled preset. `docs/media/banner.png` uses the same synthetic scene and locally installed [Liberation Mono](https://github.com/liberationfonts/liberation-fonts) (SIL Open Font License 1.1). The PNG renders the text and the repository contains no font files.
- `src/photo_styler/static/favicon.png` is an original geometric mark drawn for this release.
- **Red CRT** and **Dusk Cyan Artwork** contain numeric filter settings, flags, a format name and hex color values. They match the corresponding Travel Grid Photo Styler prototype settings documented by the same contributor who imported them into the standalone MIT-licensed project. The preset files contain no image assets or executable code.


### Showcase photographs

The three source photographs have documented public-domain status. The local JPEGs were resized, re-encoded and stripped of metadata. Each corresponding WebP is a screenshot of Photo Styler processing that JPEG in Chromium. The displayed colors and effects come from the app. The agencies are credited as image sources.

| Local files | Credit and rights | Source record and original download |
| --- | --- | --- |
| `chicago-original.jpg`, `chicago-app.webp` | Image courtesy of the Earth Science and Remote Sensing Unit, NASA Johnson Space Center. U.S. public domain, [NASA use guidelines](https://eol.jsc.nasa.gov/collections/earthfromspace/guidelines.htm). | [ISS-37 Lake Michigan, Chicago, IL](https://commons.wikimedia.org/wiki/File:ISS-37_Lake_Michigan,_Chicago,_IL.jpg) · [original JPEG](https://upload.wikimedia.org/wikipedia/commons/2/25/ISS-37_Lake_Michigan%2C_Chicago%2C_IL.jpg) |
| `death-valley-original.jpg`, `death-valley-app.webp` | Paul Stone, U.S. Geological Survey. The USGS record marks the photo Public Domain. | [Death Valley Dunes](https://www.usgs.gov/media/images/death-valley-dunes-0) · [original JPEG](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/thumbnails/image/death%20valley%20dunes_PStone_0.jpg) |
| `hoover-dam-original.jpg`, `hoover-dam-app.webp` | U.S. Bureau of Reclamation photographer, 22 May 1935. U.S. public domain as a federal work. | [Upstream face of Hoover Dam](https://commons.wikimedia.org/wiki/File:Damupstream.jpg) · [original JPEG](https://upload.wikimedia.org/wikipedia/commons/8/8f/Damupstream.jpg) |

The source photographs retain their public-domain status. The MIT license covers the Photo Styler code and original interface shown in the screenshots.
