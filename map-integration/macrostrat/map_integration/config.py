"""
Settings that define the ingestion process.
"""

from macrostrat.core.config import settings  # type: ignore[import-untyped]

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
TIMEOUT = 60  # seconds

PG_DATABASE = getattr(settings, "pg_database")
S3_HOST = getattr(settings, "s3_host", None)
S3_ACCESS_KEY = getattr(settings, "s3_access_key", None)
S3_SECRET_KEY = getattr(settings, "s3_secret_key", None)
