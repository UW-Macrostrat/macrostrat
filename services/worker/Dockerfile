# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=py-modules map-utils /app/map-utils
COPY --from=py-modules column-ingestion /app/column-ingestion
COPY . /app/worker

RUN pip install --no-cache-dir ./map-utils ./column-ingestion ./worker[maps,columns]

# Consume the maps + columns queues (one worker for both, locally).
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps,columns", "--loglevel=info", "--concurrency=2"]
