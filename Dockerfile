FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df AS build

WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.13.9
COPY pyproject.toml uv.lock README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY src/ src/
RUN uv sync --locked --no-editable --no-dev --no-python-downloads

FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

RUN groupadd --gid 10001 photo-styler \
    && useradd --uid 10001 --gid 10001 --no-create-home photo-styler \
    && install -d -m 0700 -o 10001 -g 10001 /data
COPY --from=build /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PHOTO_STYLER_HOST=0.0.0.0 \
    PHOTO_STYLER_DATA_DIR=/data
USER 10001:10001
VOLUME ["/data"]
EXPOSE 8765

CMD ["photo-styler"]
