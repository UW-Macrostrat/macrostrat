# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# macrostrat.map_utils lives in py-modules, supplied as a named build context
# (see the `additional_contexts` in docker-compose.yaml). The worker package
# itself is the main build context.
COPY --from=py-modules map-utils /app/map-utils
COPY . /app/worker

RUN pip install --no-cache-dir ./map-utils ./worker[maps]

# Consume only the `maps` queue; Can add future queues down the road
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps", "--loglevel=info", "--concurrency=2"]
