"""
Settings that define the ingestion process.
"""

from macrostrat.core.config import settings  # type: ignore[import-untyped]

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
TIMEOUT = 10  # seconds

PG_DATABASE = settings.pg_database
S3_HOST = settings.s3_host
S3_ACCESS_KEY = settings.s3_access_key
S3_SECRET_KEY = settings.s3_secret_key
S3_BUCKET = settings.s3_bucket
S3_PREFIX = settings.s3_prefix
