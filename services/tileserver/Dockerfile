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

# One level deeper than the other services: the raster libraries are referenced
# from a sibling checkout (`../../../python-libraries/...`), and uv refuses a
# relative path that climbs above the filesystem root. `/macrostrat` gives that
# path somewhere to land.
WORKDIR /macrostrat/services/main

# Create a virtual environment for the app; add virtualenv and UV to PATH
RUN python3.11 -m venv .venv
ENV PATH="/macrostrat/services/main/.venv/bin:$PATH" \
    VIRTUAL_ENV=/venv

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# NEED TO specify another build context for the py-modules directory
COPY --from=py-modules tileserver-utils /macrostrat/py-modules/tileserver-utils

# The raster libraries are developed in the Python-libraries monorepo and are not
# yet released, so they arrive through their own build context, landing where the
# `../../../python-libraries/...` sources in pyproject.toml resolve to. Drop this
# once the packages are published to PyPI.
COPY --from=python-libraries raster-index /python-libraries/raster-index
COPY --from=python-libraries raster-layers /python-libraries/raster-layers

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

ADD . /macrostrat/services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.tileserver:app" ]
