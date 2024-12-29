"""
Settings that define the ingestion process.
"""

from macrostrat.core.config import settings  # type: ignore[import-untyped]

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
TIMEOUT = 60  # seconds

PG_DATABASE = getattr(settings, "pg_database")

storage = getattr(settings, "storage", {})
buckets = getattr(settings, "buckets", {})

S3_HOST = storage.get("host", None)
ACCESS_KEY = storage.get("access_key", None)
SECRET_KEY = storage.get("secret_key", None)
S3_BUCKET = buckets.get("map-staging", None)
