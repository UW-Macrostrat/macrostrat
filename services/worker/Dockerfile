# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=py-modules map-utils /app/map-utils
COPY . /app/worker

RUN pip install --no-cache-dir ./map-utils ./worker[maps]

# Consume only the `maps` queue; Can add future queues down the road
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps", "--loglevel=info", "--concurrency=2"]
