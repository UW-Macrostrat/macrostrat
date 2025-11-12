FROM ghcr.io/osgeo/gdal:ubuntu-small-3.11.0

# Install python from deadsnakes PPA
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  software-properties-common && \
  add-apt-repository ppa:deadsnakes/ppa && \
  apt-get update -y && \
  apt-get install -y --no-install-recommends \
    gdb \
    g++ \
    make \
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

# NEED TO specify another build context for the py-modules directory
COPY --from=py-modules tileserver-utils /py-modules/tileserver-utils

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=deps,target=deps \
    uv sync --locked --no-install-project --no-editable

ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.tileserver:app" ]
