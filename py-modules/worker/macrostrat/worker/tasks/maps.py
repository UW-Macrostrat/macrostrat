"""
Map-related Celery tasks.

tasks delegate to `macrostrat.map_utils`
"""

import os

from macrostrat.database import Database
from macrostrat.map_utils import StorageConfig, delete_map

from macrostrat.worker.app import app


def _database() -> Database:
    url = os.environ.get("DB_URL")
    if not url:
        raise RuntimeError("DB_URL environment variable is not set")
    return Database(url)


def _storage() -> StorageConfig | None:
    """Build a StorageConfig from env, or None to run a DB-only delete."""
    endpoint = os.environ.get("S3_ENDPOINT")
    bucket = os.environ.get("S3_BUCKET")
    if not endpoint or not bucket:
        return None
    return StorageConfig(
        endpoint=endpoint,
        access_key=os.environ.get("S3_ACCESS_KEY", ""),
        secret_key=os.environ.get("S3_SECRET_KEY", ""),
        bucket=bucket,
        secure=os.environ.get("S3_SECURE", "false").lower() == "true",
    )


@app.task(name="macrostrat.maps.delete")
def delete_map_task(slug: str) -> dict:
    """Delete a staged map by slug (DB + optional S3 staging cleanup)."""
    db = _database()
    return delete_map(db, slug, storage=_storage())
