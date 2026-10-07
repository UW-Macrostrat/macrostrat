"""
This is the single source of truth for deleting a staged map. so
it can be imported by the Celery worker, the API, and the CLI etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from psycopg.sql import Identifier

from macrostrat.database import Database

from .slugs import staging_table


@dataclass
class StorageConfig:
    """Connection details for the S3/MinIO map-ingest bucket."""

    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    secure: bool = True


def _delete_staging_objects(db: Database, slug: str, storage: StorageConfig) -> int:
    """removes every staged object linked to the map in ``maps_metadata.map_files``.
    this deletes all matching objects with no promp. The database is the source of truth:
     for each object we unlink its ingest references, delete the storage row, then remove it from MinIO.
    """
    from minio import Minio

    objects = (
        db.run_query(
            """
            SELECT o.id, o.key
            FROM storage.objects o
            JOIN maps_metadata.map_files f ON f.object_id = o.id
            JOIN maps.sources s ON s.source_id = f.source_id
            WHERE o.scheme = 's3'
              AND o.host = :host
              AND o.bucket = :bucket
              AND s.slug = :slug
            ORDER BY o.key
            """,
            dict(host=storage.endpoint, bucket=storage.bucket, slug=slug),
        )
        .mappings()
        .all()
    )
    if not objects:
        return 0

    client = Minio(
        storage.endpoint,
        access_key=storage.access_key,
        secret_key=storage.secret_key,
        secure=storage.secure,
    )

    for obj in objects:
        db.run_sql(
            "DELETE FROM maps_metadata.map_files WHERE object_id = :object_id",
            dict(object_id=obj["id"]),
        )
        db.run_sql(
            "DELETE FROM storage.objects WHERE id = :id",
            dict(id=obj["id"]),
        )
        try:
            client.remove_object(storage.bucket, obj["key"])
        except Exception as err:  # best-effort object removal
            print(f"[map_utils] failed to remove {obj['key']} from MinIO: {err}")

    return len(objects)


def delete_map(
    db: Database, slug: str, *, storage: StorageConfig | None = None
) -> dict:
    """Delete a staged map by slug.

    Drops the source geometry tables, optionally clears staged S3 objects, and
    removes the ingest process and source rows
    Returns a summary dict. Pass ``storage`` to also clean the staging bucket;
    omit it for a DB-only delete.
    """
    tables = db.run_query(
        "SELECT primary_table, primary_line_table FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).fetchone()

    line_table = tables.primary_line_table if tables is not None else None
    poly_table = tables.primary_table if tables is not None else None
    if line_table is None:
        line_table = staging_table(slug, "lines")
    if poly_table is None:
        poly_table = staging_table(slug, "polygons")
    points_table = staging_table(slug, "points")

    for table in (line_table, poly_table, points_table):
        db.run_sql(
            "DROP TABLE IF EXISTS {table}",
            dict(table=Identifier("sources", table)),
        )

    objects_removed = 0
    if storage is not None:
        objects_removed = _delete_staging_objects(db, slug, storage)

    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    # Delete all ingest-related rows for this source, then the source itself.
    db.run_sql(
        "DELETE FROM maps_metadata.ingest_process_tag WHERE source_id = :source_id",
        dict(source_id=source_id),
    )
    db.run_sql(
        "DELETE FROM maps_metadata.ingest_process WHERE source_id = :source_id",
        dict(source_id=source_id),
    )
    db.run_sql("DELETE FROM maps.sources WHERE slug = :slug", dict(slug=slug))

    return {"slug": slug, "source_id": source_id, "objects_removed": objects_removed}
