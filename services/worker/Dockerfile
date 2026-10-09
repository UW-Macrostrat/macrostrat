# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=py-modules map-utils /app/map-utils
COPY --from=py-modules column-utils /app/column-utils
COPY --from=py-modules column-ingestion /app/column-ingestion
# column-ingestion depends on macrostrat.core and macrostrat.column-utils,
# monorepo-internal packages (not published to PyPI). pip ignores the
# [tool.uv.sources] editable paths that resolve them in the workspace, so they
# must be copied and installed from source here. Its own deps (macrostrat.app-frame, macrostrat.database,
# ...) are published and resolve from the index.
COPY --from=py-modules core /app/core
# Management tasks: the runner, the topology library and the topology-manager
# submodule it builds on (a git submodule, not a published package, so it is
# installed from source like the monorepo packages).
COPY --from=py-modules task-runner /app/task-runner
COPY --from=py-modules map-topology /app/map-topology
COPY --from=submodules topology-manager /app/topology-manager
COPY . /app/worker

RUN pip install --no-cache-dir ./map-utils ./core ./column-utils ./column-ingestion \
    ./task-runner ./topology-manager ./map-topology[topology] ./worker[maps,columns,tasks]

# Build information, set by CI. Last, so a new commit leaves the layers above cached.
ARG MACROSTRAT_VERSION MACROSTRAT_RELEASE MACROSTRAT_COMMIT MACROSTRAT_BUILD_DATE MACROSTRAT_REPOSITORY
ENV MACROSTRAT_VERSION=$MACROSTRAT_VERSION \
    MACROSTRAT_RELEASE=$MACROSTRAT_RELEASE \
    MACROSTRAT_COMMIT=$MACROSTRAT_COMMIT \
    MACROSTRAT_BUILD_DATE=$MACROSTRAT_BUILD_DATE \
    MACROSTRAT_REPOSITORY=$MACROSTRAT_REPOSITORY

# Consume the maps + columns queues (one worker for both, locally).
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps,columns", "--loglevel=info", "--concurrency=2"]
