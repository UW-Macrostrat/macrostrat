FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.0

# Install python from deadsnakes PPA.
# `libpq-dev` is here because macrostrat.database 4.x depends on `psycopg2`
# rather than `psycopg2-binary`, so it is built from source and needs libpq headers.
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa && \
  apt-get update -y && \
  apt-get install -y --no-install-recommends \
    gdb \
    g++ \
    make \
    libpq-dev \
    python3.11 \
    python3.11-venv \
    python3.11-dev && \
  rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/
# https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers

WORKDIR /services/main

# Create a virtual environment for the app; add virtualenv and UV to PATH
RUN python3.11 -m venv .venv
ENV PATH="/services/main/.venv/bin:$PATH" \
    VIRTUAL_ENV=/venv

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# GDAL network behaviour for cloud-optimized rasters read over HTTP (the
# `/rasters` mosaics and the elevation service). With the defaults, opening one
# remote COG costs a HEAD request, a directory-listing attempt and a 404 probe
# for each of `.aux.xml` / `.ovr` / `.msk` before the header is read; these are
# the settings titiler's own images ship to avoid that. `CPL_VSIL_CURL_CACHE_SIZE`
# is the cross-open byte cache that makes a re-read of a file already touched
# cost milliseconds — headers included — so it is sized to hold many of them.
# `CPL_VSIL_CURL_ALLOWED_EXTENSIONS` is deliberately not set: it would break the
# generic `/cog` route for anything that is not a `.tif`.
ENV GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR \
    GDAL_INGESTED_BYTES_AT_OPEN=32768 \
    GDAL_HTTP_VERSION=2 \
    GDAL_HTTP_MULTIPLEX=YES \
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES \
    CPL_VSIL_CURL_CACHE_SIZE=536870912 \
    GDAL_CACHEMAX=512 \
    VSI_CACHE=TRUE \
    VSI_CACHE_SIZE=52428800

# NEED TO specify another build context for the py-modules directory
COPY --from=py-modules tileserver-utils /py-modules/tileserver-utils

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

EXPOSE 8000

# Trust X-Forwarded-Proto from the proxy in front (Varnish, then the ingress), so
# URLs built from the request (tilejson `tiles`) keep the client's https scheme.
CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "macrostrat.tileserver:app" ]
