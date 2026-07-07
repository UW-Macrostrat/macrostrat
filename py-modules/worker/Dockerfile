# See docker-compose.yaml `celery_worker`.
FROM python:3.12-slim

WORKDIR /app

COPY map-utils /app/map-utils
COPY worker /app/worker

RUN pip install --no-cache-dir ./map-utils ./worker[maps]

# Consume only the `maps` queue; Can add future queues down the road
CMD ["celery", "-A", "macrostrat.worker.app", "worker", "-Q", "maps", "--loglevel=info", "--concurrency=2"]
