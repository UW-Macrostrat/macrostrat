# Usage-stats worker.
#
# Runs the harvester on a schedule (Kubernetes CronJob), ingesting Traefik
# access-log dumps from object storage into the usage_stats schema. Replaces the
# previous image here, a standalone worker that polled a Matomo database that no
# longer exists.
#
# The logic lives in the macrostrat.usage_stats_capture library; this service is
# the frontend that reads configuration from the environment. Configuration is
# entirely environmental — see usage_stats_service/config.py.
#
# BUILD CONTEXT IS THE REPOSITORY ROOT, because the service depends on a library
# under py-modules/:
#
#   docker build -f services/usage-stats/Dockerfile .

# --- build stage -------------------------------------------------------------
# psycopg2 publishes only Windows wheels, so on Linux it compiles from sdist and
# needs a compiler plus libpq headers. build-essential rather than bare gcc: the
# latter omits libc6-dev, and the build then fails on a missing stdlib.h. All of
# it stays here; the runtime image gets the built venv and libpq alone.
FROM python:3.12-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/services/usage-stats

# The library first: it changes less often than the service wrapper, so it
# caches better.
COPY py-modules/usage-stats-capture /app/py-modules/usage-stats-capture

# Dependencies before source, so edits to the service don't re-resolve.
COPY services/usage-stats/pyproject.toml services/usage-stats/uv.lock \
     services/usage-stats/README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY services/usage-stats /app/services/usage-stats
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- runtime -----------------------------------------------------------------
FROM python:3.12-slim

# libpq5 only — the runtime half of the psycopg2 build above.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
 && rm -rf /var/lib/apt/lists/*

# The venv records absolute paths, so it has to land where it was built.
COPY --from=build /app /app
ENV PATH="/app/services/usage-stats/.venv/bin:${PATH}"

WORKDIR /app/services/usage-stats

# No console script: the worker has no CLI framework, just this module.
ENTRYPOINT ["python", "-m", "usage_stats_service"]
