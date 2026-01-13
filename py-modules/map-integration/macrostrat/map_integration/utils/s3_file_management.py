import hashlib
import json
import mimetypes
import pathlib
import shutil
import subprocess
import tempfile
from os import path
from pathlib import Path
from textwrap import dedent

from minio import Minio
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from macrostrat.core import app as app_
from macrostrat.core.exc import MacrostratError
from macrostrat.core.schemas import SchemeEnum

settings = app_.settings
console = Console()


def guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or "application/octet-stream"


def get_minio_client():
    return Minio(
        endpoint=settings.get("storage.endpoint"),
        access_key=settings.get("storage.access_key"),
        secret_key=settings.get("storage.secret_key"),
        secure=True,
    )


def make_zip_for_data_path(*, slug: str, data_path: Path) -> Path:
    tmp_dir = Path(tempfile.gettempdir()) / "macrostrat_upload_zips"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    unique = next(tempfile._get_candidate_names())
    archive_base = tmp_dir / f"{slug}_{unique}"
    base_name = str(archive_base)

    if data_path.is_dir() or data_path.is_file():
        archive_path = shutil.make_archive(
            base_name,
            "zip",
            root_dir=str(data_path.parent),
            base_dir=str(data_path.name),
        )
        return Path(archive_path)

    raise FileNotFoundError(f"data_path does not exist or is unsupported: {data_path}")


def sha256_of_file(p: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def print_objects(objects: list[dict]) -> None:
    table = Table(title="Objects selected")

    table.add_column("#", justify="right")
    table.add_column("Object ID", justify="right")
    table.add_column("Key")
    for i, obj in enumerate(objects, start=1):
        table.add_row(str(i), str(obj["id"]), obj["key"])
    console.print(table)


def parse_selection(selection: str, objects: list[dict]) -> list[dict]:
    """input: * → delete everything,obj_ids separated by commas or a hyphen"""
    if selection.strip() == "*":
        return objects
    selected = set()
    try:
        parts = selection.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                for i in range(int(start), int(end) + 1):
                    selected.add(i)
            else:
                selected.add(int(part))
    except ValueError:
        return []
    return [objects[i - 1] for i in sorted(selected) if 1 <= i <= len(objects)]


# --------------UPLOADS---------------


def get_existing_object_id(db, *, host: str, bucket: str, key: str) -> int | None:
    return db.run_query(
        """
        SELECT id
        FROM storage.object
        WHERE scheme = 's3'
          AND host = :host
          AND bucket = :bucket
          AND key = :key
        """,
        dict(host=host, bucket=bucket, key=key),
    ).scalar()


def insert_storage_object(
    db,
    *,
    host: str,
    bucket: str,
    key: str,
    sha256: str,
    mime_type: str,
) -> int:
    db.run_sql(
        """
        INSERT INTO storage.object
          (scheme, host, bucket, key, source, sha256_hash, mime_type)
        VALUES
          ('s3', :host, :bucket, :key, :source, :sha256, :mime_type)
        """,
        dict(
            host=host,
            bucket=bucket,
            key=key,
            source=json.dumps({}),
            sha256=sha256,
            mime_type=mime_type,
        ),
    )
    object_id = get_existing_object_id(db, host=host, bucket=bucket, key=key)
    if object_id is None:
        raise RuntimeError("Failed to retrieve storage.object id after insert")
    return object_id


def link_object_to_ingest(
    db,
    *,
    ingest_process_id: int,
    object_id: int,
) -> None:
    db.run_sql(
        """
        INSERT INTO maps_metadata.map_files (ingest_process_id, object_id)
        VALUES (:ingest_process_id, :object_id)
        ON CONFLICT DO NOTHING
        """,
        dict(
            ingest_process_id=ingest_process_id,
            object_id=object_id,
        ),
    )


def upload_file_to_minio(
    minio_client: Minio,
    *,
    bucket: str,
    object_key: str,
    local_path: Path,
    sha256: str,
) -> None:
    with open(local_path, "rb") as f:
        minio_client.put_object(
            bucket_name=bucket,
            object_name=object_key,
            data=f,
            length=local_path.stat().st_size,
            metadata={"sha256": sha256},
        )


def staging_upload_dir(
    slug: str,
    data_path: Path,
    db,
    ingest_process_id: int,
) -> dict:
    """
    Upload local files to S3 via MinIO and register them in storage.object.
    Always uploads a single zip archive for the provided data_path.
    """
    if ingest_process_id is None:
        raise ValueError("ingest_process_id is required to link uploaded files")

    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    minio_client = get_minio_client()

    zip_path = make_zip_for_data_path(slug=slug, data_path=data_path)
    rel_key = f"{slug}.zip"
    object_key = f"{slug}/{rel_key}"

    uploaded_object_ids: list[int] = []

    try:
        existing_id = get_existing_object_id(
            db,
            host=host,
            bucket=bucket,
            key=object_key,
        )
        if existing_id:
            return {
                "bucket_name": bucket,
                "slug": slug,
                "endpoint": host,
                "destination": f"s3://{bucket}/{slug}/",
                "objects_created": [],
                "note": "Object already exists; skipping upload.",
            }

        sha256 = sha256_of_file(zip_path)
        mime_type = "application/zip"

        upload_file_to_minio(
            minio_client,
            bucket=bucket,
            object_key=object_key,
            local_path=zip_path,
            sha256=sha256,
        )

        object_id = insert_storage_object(
            db,
            host=host,
            bucket=bucket,
            key=object_key,
            sha256=sha256,
            mime_type=mime_type,
        )

        link_object_to_ingest(
            db,
            ingest_process_id=ingest_process_id,
            object_id=object_id,
        )

        uploaded_object_ids.append(object_id)

        return {
            "bucket_name": bucket,
            "slug": slug,
            "endpoint": host,
            "destination": f"s3://{bucket}/{slug}/",
            "objects_created": uploaded_object_ids,
        }

    finally:
        try:
            zip_path.unlink(missing_ok=True)
        except Exception:
            pass


# --------------------DELETIONS-------------------
def confirm_delete(count: int) -> bool:
    resp = (
        input(f"\nDelete {count} object(s)? Type 'yes' or 'y' to confirm: ")
        .strip()
        .lower()
    )
    return resp == "yes" or resp == "y"


def get_objects_for_slug(db, *, host: str, bucket: str, slug: str) -> list[dict]:
    return (
        db.run_query(
            """
        SELECT id, key
        FROM storage.object
        WHERE scheme = 's3'
          AND host = :host
          AND bucket = :bucket
          AND key LIKE :prefix
        ORDER BY key
        """,
            dict(
                host=host,
                bucket=bucket,
                prefix=f"{slug}/%",
            ),
        )
        .mappings()
        .all()
    )


def unlink_object_from_ingests(db, *, object_id: int) -> None:
    db.run_sql(
        """
        DELETE FROM maps_metadata.map_files
        WHERE object_id = :object_id
        """,
        dict(object_id=object_id),
    )


def delete_storage_object(db, *, object_id: int) -> None:
    db.run_sql(
        """
        DELETE FROM storage.object
        WHERE id = :id
        """,
        dict(id=object_id),
    )


def delete_object_from_minio(
    minio_client: Minio,
    *,
    bucket: str,
    object_key: str,
) -> None:
    try:
        minio_client.remove_object(bucket, object_key)
    except Exception as e:
        console.print(f"[red]Failed to delete {object_key}: {e}[/red]")


def staging_delete_dir(slug: str, db) -> dict:
    """
    Delete all staged objects under a slug using DB as the source of truth.
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    minio_client = get_minio_client()

    objects = get_objects_for_slug(
        db,
        host=host,
        bucket=bucket,
        slug=slug,
    )

    if not objects:
        console.print("[yellow]No objects found for this slug.[/yellow]")
        return {"objects_deleted": 0}
    print_objects(objects)
    selection = input(
        "\nEnter '*' to delete all, or specify items (e.g. 1,3-5): "
    ).strip()
    selected_objects = parse_selection(selection, objects)
    if not selected_objects:
        console.print("[red]No valid objects selected. Aborting.[/red]")
        return {"objects_deleted": 0}
    console.print("\n[bold]Selected for deletion:[/bold]")
    print_objects(selected_objects)
    if not confirm_delete(len(selected_objects)):
        console.print("[yellow]Deletion cancelled.[/yellow]")
        return {"objects_deleted": 0}

    deleted = []

    for obj in selected_objects:
        object_id = obj["id"]
        object_key = obj["key"]
        # Remove ingest links
        unlink_object_from_ingests(db, object_id=object_id)
        # Remove DB object record
        delete_storage_object(db, object_id=object_id)
        # Remove from MinIO
        delete_object_from_minio(
            minio_client,
            bucket=bucket,
            object_key=object_key,
        )
        deleted.append(object_key)

    console.print(f"[green]Deleted {len(deleted)} object(s).[/green]")

    return {
        "bucket": bucket,
        "slug": slug,
        "objects_deleted": len(deleted),
        "keys": deleted,
    }


# ----------------LISTS------------------


def staging_list_dir(
    db,
    slug: str,
    page_token: int = 0,
    page_size: int = 20,
) -> dict:
    """
    List staged objects using the database as the source of truth.
    Supports pagination via page_token / page_size.
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")

    # --- Fetch objects ---
    if slug == "all":
        objects = (
            db.run_query(
                """
            SELECT id, key
            FROM storage.object
            WHERE scheme = 's3'
              AND host = :host
              AND bucket = :bucket
            ORDER BY key
            """,
                dict(host=host, bucket=bucket),
            )
            .mappings()
            .all()
        )
    else:
        objects = get_objects_for_slug(
            db,
            host=host,
            bucket=bucket,
            slug=slug,
        )

    total = len(objects)

    # --- Pagination ---
    start = page_token
    end = page_token + page_size
    page = objects[start:end]

    next_page_token = end if end < total else None
    print_objects(page)

    return {
        "files": [obj["key"] for obj in page],
        "next_page_token": next_page_token,
        "total": total,
    }


def staging_download_dir(db, slug: str, dest_path: Path) -> dict:
    """
    Interactively select and download staged objects using the DB
    as the source of truth.
    """
    bucket = settings.get("storage.bucket_name")
    host = settings.get("storage.endpoint")
    minio_client = get_minio_client()

    # Fetch objects from DB
    if slug == "all":
        objects = (
            db.run_query(
                """
            SELECT id, key
            FROM storage.object
            WHERE scheme = 's3'
              AND host = :host
              AND bucket = :bucket
            ORDER BY key
            """,
                dict(host=host, bucket=bucket),
            )
            .mappings()
            .all()
        )
    else:
        objects = get_objects_for_slug(
            db,
            host=host,
            bucket=bucket,
            slug=slug,
        )

    if not objects:
        console.print("[yellow]No objects found.[/yellow]")
        return {"downloaded": 0}

    # Show available objects
    print_objects(objects)

    selection = input(
        "\nEnter '*' to download all, or specify items (e.g. 1,3-5): "
    ).strip()

    selected_objects = parse_selection(selection, objects)
    if not selected_objects:
        console.print("[red]No valid objects selected. Aborting.[/red]")
        return {"downloaded": 0}

    console.print("\n[bold]Selected for download:[/bold]")
    print_objects(selected_objects)

    dest_path.mkdir(parents=True, exist_ok=True)

    downloaded = []

    for obj in selected_objects:
        object_key = obj["key"]

        # Strip slug prefix to preserve relative paths
        rel_path = object_key.split("/", 1)[1] if "/" in object_key else object_key
        local_path = dest_path / rel_path
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            response = minio_client.get_object(bucket, object_key)
            with open(local_path, "wb") as f:
                for chunk in response.stream(32 * 1024):
                    f.write(chunk)
            downloaded.append(str(local_path))
        except Exception as e:
            console.print(f"[red]Failed to download {object_key}: {e}[/red]")

    console.print(f"[green]Downloaded {len(downloaded)} file(s).[/green]")

    return {
        "bucket": bucket,
        "slug": slug,
        "downloaded": len(downloaded),
        "paths": downloaded,
    }
