# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

# psycopg2 builds from source; uv caches the wheel it builds.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.3 /uv /uvx /bin/

WORKDIR /services/main

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/services/main/.venv/bin:$PATH"

# Install published dependencies before local modules, so editing those keeps this layer.
# `--frozen`: `--locked` would need the local modules' pyproject.toml to check the lock.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-install-local --no-editable --all-extras

# Paths match the lockfile's relative sources from /services/main.
COPY --from=py-modules map-utils /py-modules/map-utils
COPY --from=py-modules core /py-modules/core
COPY --from=py-modules column-utils /py-modules/column-utils
COPY --from=py-modules column-ingestion /py-modules/column-ingestion
COPY --from=py-modules task-runner /py-modules/task-runner
COPY --from=py-modules map-topology /py-modules/map-topology
COPY --from=submodules topology-manager /submodules/topology-manager
# The map-processing pipeline. Its GIS libraries ship as wheels, so no system
# GDAL; the `gis` extra with the GDAL bindings is left out.
COPY --from=py-modules map-integration /py-modules/map-integration
COPY --from=py-modules match-utils /py-modules/match-utils

ADD . /services/main

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --all-extras

# Build information, set by CI. Last, so a new commit leaves the layers above cached.
ARG MACROSTRAT_VERSION MACROSTRAT_RELEASE MACROSTRAT_COMMIT MACROSTRAT_BUILD_DATE MACROSTRAT_REPOSITORY
ENV MACROSTRAT_VERSION=$MACROSTRAT_VERSION \
    MACROSTRAT_RELEASE=$MACROSTRAT_RELEASE \
    MACROSTRAT_COMMIT=$MACROSTRAT_COMMIT \
    MACROSTRAT_BUILD_DATE=$MACROSTRAT_BUILD_DATE \
    MACROSTRAT_REPOSITORY=$MACROSTRAT_REPOSITORY

# Consume the maps + columns queues (one worker for both, locally).
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps,columns", "--loglevel=info", "--concurrency=2"]
