# Debian's own Mapnik and its Python bindings, on the system interpreter, in
# place of a from-source Mapnik build against a bullseye-era base (unbuildable
# since bullseye left LTS). `python3-mapnik` is the same upstream commit the
# build used to compile, and `libmapnik3.1` carries the PostGIS input plugin.
FROM debian:bookworm-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1
# The system interpreter is the one the Mapnik bindings are built for.
ENV UV_PYTHON_DOWNLOADS=never

# node-carto converts CartoCSS to Mapnik XML at startup.
RUN apt-get update -y && \
  apt-get install -y --no-install-recommends \
  python3 python3-venv python3-mapnik node-carto ca-certificates && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /services/main

# System site packages, so the venv sees Debian's mapnik module.
RUN uv venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

# NEED TO specify a build context for the py-modules directory
COPY --from=py-modules tileserver-utils /py-modules/tileserver-utils

# `--inexact` leaves the venv's extra packages alone.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --inexact --locked --no-install-project --no-editable --active

# Add source files to project
ADD . /services/main

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --inexact --locked --no-editable --active

# Check that the Mapnik bindings and the CartoCSS compiler are reachable
RUN python -c "import mapnik; print('mapnik version:', mapnik.mapnik_version())" && \
    python -c "import uvicorn; print('uvicorn version:', uvicorn.__version__)" && \
    carto --version

EXPOSE 8000

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8000", "macrostrat.legacy_tileserver:app"]
