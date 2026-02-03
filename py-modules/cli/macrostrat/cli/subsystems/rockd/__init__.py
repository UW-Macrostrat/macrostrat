import asyncio
import importlib
import time
from datetime import datetime, timedelta, timezone
from os import environ
from pathlib import Path
from typing import Any

import typer
from minio import Minio
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.status import Status
from rich.table import Table
from sqlalchemy import text
from typer import Argument, Option, Typer

from macrostrat.cli.database.utils import engine_for_db_name
from macrostrat.core import app as app_
from macrostrat.core.migrations import _run_migrations
from macrostrat.database import Database
from macrostrat.database.transfer import pg_dump_to_file, pg_restore_from_file

from ..storage import s3_bucket_migration

cli = Typer(help="Rockd database tools")
settings = app_.settings
console = Console()
DUMP_BUCKET = "rockd-database-dumps"
DUMP_SUFFIX = ".rockd.pg_dump"
DEFAULT_LIMIT = 5
DEFAULT_LOOKBACK_DAYS = 10


def get_rockd_db() -> Database:
    """
    Return a Database instance that talks to the Rockd cluster.
    The URL can live in .env / docker-compose.yml as ROCKD_DATABASE.
    """
    url = environ.get("ROCKD_DATABASE")
    if url is None:
        raise RuntimeError("Set ROCKD_DATABASE in your environment")
    return Database(url)


def parse_dump_datetime(object_name: str) -> datetime | None:
    # "2026-01-30T00:00:12.rockd.pg_dump"
    ts = object_name.split(".", 1)[0]
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def rockd_v1_s3_connection() -> Minio:
    endpoint = settings.get("storage.endpoint")
    access_key = settings.get("storage.rockd_backup_access")
    secret_key = settings.get("storage.rockd_backup_secret")

    secure = True
    if endpoint.startswith("https://"):
        endpoint = endpoint.removeprefix("https://")
        secure = True
    elif endpoint.startswith("http://"):
        endpoint = endpoint.removeprefix("http://")
        secure = False

    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def list_recent_rockd_dumps(
    minio_client: Minio,
    *,
    bucket: str = DUMP_BUCKET,
    limit: int = DEFAULT_LIMIT,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[dict[str, Any]]:
    """
    Optimized bounded scan: iterate day prefixes newest->oldest and stop early once we have `limit` dumps.
    Returns objects as dicts: {idx, key, size, dt}
    """
    now_utc = datetime.now(timezone.utc)
    found: list[tuple[datetime, Any]] = []

    for i in range(lookback_days):
        day_prefix = (now_utc - timedelta(days=i)).strftime("%Y-%m-%d")

        # Filenames are flat -> recursive=False is enough
        for obj in minio_client.list_objects(
            bucket, prefix=day_prefix, recursive=False
        ):
            if not obj.object_name.endswith(DUMP_SUFFIX):
                continue
            dt = parse_dump_datetime(obj.object_name)
            if dt is None:
                continue
            found.append((dt, obj))
            if len(found) >= limit:
                break

        if len(found) >= limit:
            break

    # Sort newest -> oldest by filename timestamp
    found.sort(key=lambda x: x[0], reverse=True)

    results: list[dict[str, Any]] = []
    for idx, (dt, obj) in enumerate(found[:limit], start=1):
        results.append(
            {
                "idx": idx,
                "key": obj.object_name,
                "size": obj.size,
                "dt": dt,
            }
        )
    return results


def print_dump_table(objects: list[dict[str, Any]]) -> None:
    table = Table(title="Recent Rockd dumps")
    table.add_column("#", justify="right")
    table.add_column("Timestamp (UTC)")
    table.add_column("Size", justify="right")
    table.add_column("Key")

    for obj in objects:
        size_mib = obj["size"] / 1024 / 1024
        table.add_row(
            str(obj["idx"]),
            obj["dt"].isoformat(),
            f"{size_mib:,.1f} MiB",
            obj["key"],
        )
    console.print(table)


def download_object_with_progress(
    minio_client: Minio,
    *,
    bucket: str,
    object_key: str,
    dest_path: Path,
    size: int,
) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    progress = Progress(
        TextColumn("[bold]download[/bold]"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task("download", total=size)

        response = minio_client.get_object(bucket, object_key)
        try:
            with open(dest_path, "wb") as f:
                for chunk in response.stream(1024 * 1024):  # 1 MiB
                    f.write(chunk)
                    progress.update(task_id, advance=len(chunk))
        finally:
            response.close()
            response.release_conn()

    return dest_path


@cli.command()
def migrations(
    apply: bool = Option(False, "--apply", help="Actually run them"),
    name: str | None = None,
    force: bool = False,
    data_changes: bool = False,
):
    """
    List or apply Rockd migrations.
    """
    importlib.import_module(".migrations", __package__)
    db = get_rockd_db()

    with db.engine.connect() as conn:
        row = (
            conn.execute(
                text(
                    """
            select current_database() as db,
                   current_user     as usr,
                   inet_server_addr() as host,
                   inet_server_port() as port,
                   to_regclass('public.people') as ppl,
                   to_regclass('public.checkins') as chk
        """
                )
            )
            .mappings()
            .one()
        )
        print(
            f"Preflight -> db={row['db']} user={row['usr']} server={row['host']}:{row['port']} people={row['ppl']} checkins={row['chk']}"
        )
    _run_migrations(
        db,
        apply=apply,
        name=name,
        force=force,
        data_changes=data_changes,
        subsystem="rockd",
    )


@cli.command()
def download_rockd_dump(
    dump_dst: str = Option(".", "--dump-dst", help="Destination directory"),
    name: str = Option(None, "--name", help="Exact dump filename/key to download"),
    latest: bool = Option(
        False, "--latest", help="Download the most recent dump without prompting"
    ),
    limit: int = Option(5, "--limit", help="How many recent dumps to show"),
    lookback_days: int = Option(10, "--lookback-days", help="How far back to search"),
):
    """
    List up to N recent dump files and download one (interactive), or download latest.
    """
    minio_client = rockd_v1_s3_connection()

    # If user provided exact name, download it directly
    if name is not None:
        st = minio_client.stat_object(DUMP_BUCKET, name)
        dest_dir = Path(dump_dst)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / Path(name).name

        console.print(f"[bold]Downloading[/bold] {name} -> {dest_path}")
        download_object_with_progress(
            minio_client,
            bucket=DUMP_BUCKET,
            object_key=name,
            dest_path=dest_path,
            size=st.size,
        )
        console.print(f"[green]Saved[/green] to {dest_path}")
        return

    # Otherwise, list recent (bounded scan, early stop)
    objects = list_recent_rockd_dumps(
        minio_client,
        bucket=DUMP_BUCKET,
        limit=limit,
        lookback_days=lookback_days,
    )
    if not objects:
        raise RuntimeError("No dump files found (within lookback window)")

    print_dump_table(objects)

    # Pick latest automatically if requested
    if latest:
        chosen = objects[0]
    else:
        choice = typer.prompt(f"Select 1-{len(objects)}", type=int)
        if choice < 1 or choice > len(objects):
            raise RuntimeError("Invalid selection")
        chosen = objects[choice - 1]

    dest_dir = Path(dump_dst)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / Path(chosen["key"]).name

    console.print(f"[bold]Downloading[/bold] {chosen['key']} -> {dest_path}")
    download_object_with_progress(
        minio_client,
        bucket=DUMP_BUCKET,
        object_key=chosen["key"],
        dest_path=dest_path,
        size=chosen["size"],
    )
    console.print(f"[green]Saved[/green] to {dest_path}")


@cli.command()
def restore_rockd_dump(
    dump_file: str = Argument(..., help="Path to the .pg_dump file to restore"),
    *,
    jobs: int = Option(None, "--jobs", "-j"),
    version: str = Option(
        None,
        "--version",
        "-v",
        help="Postgres version or docker container to restore with (e.g. 15 or postgres:15)",
    ),
    force: bool = Option(
        True,
        "--force/--no-force",
        help="Terminate existing connections to rockd/rockd_backup as needed",
    ),
    drop_backup: bool = Option(
        True,
        "--drop-backup/--keep-backup",
        help="Drop rockd_backup first if it already exists",
    ),
):
    dump_path = Path(dump_file)
    if not dump_path.exists():
        raise RuntimeError(f"Dump file not found: {dump_path}")

    db_container = app_.settings.get("pg_database_container", "postgres:15")
    if version is not None:
        db_container = version if ":" in version else f"postgres:{version}"

    target_db = "rockd"
    backup_db = "rockd_backup"

    admin_engine = engine_for_db_name("postgres")

    def terminate_connections(conn, dbname: str):
        conn.execute(
            text(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :dbname
                  AND pid <> pg_backend_pid();
                """
            ),
            {"dbname": dbname},
        )

    with admin_engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        rockd_exists = (
            conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": target_db},
            ).first()
            is not None
        )

        backup_exists = (
            conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"),
                {"n": backup_db},
            ).first()
            is not None
        )

        if backup_exists:
            if drop_backup:
                if force:
                    terminate_connections(conn, backup_db)
                conn.execute(text(f'DROP DATABASE "{backup_db}"'))
                typer.echo('Dropped existing "rockd_backup"')
                backup_exists = False
            else:
                # <-- critical missing branch in your version
                raise RuntimeError(
                    "rockd_backup already exists. Use --drop-backup to replace it."
                )

        if rockd_exists:
            if force:
                terminate_connections(conn, target_db)
            conn.execute(text(f'ALTER DATABASE "{target_db}" RENAME TO "{backup_db}"'))
            typer.echo('Renamed "rockd" -> "rockd_backup"')
            if force:
                terminate_connections(conn, backup_db)  # <-- add this
        else:
            typer.echo('No existing "rockd" database found; skipping rename')

        conn.execute(text(f'CREATE DATABASE "{target_db}"'))
        typer.echo('Created fresh empty "rockd"')

    restore_engine = engine_for_db_name(target_db)

    args = []
    if jobs is not None:
        args.extend(["--jobs", str(jobs)])
    console.print(
        f"[bold]Starting restore[/bold] from {dump_path} (this may take a few minutes)"
    )

    task = pg_restore_from_file(
        str(dump_path),
        restore_engine,
        args=args,
        postgres_container=db_container,
        create=False,
    )

    async def _run_with_heartbeat():
        start = time.time()
        with console.status(
            "[bold]Restoring (pg_restore running)...[/bold] 0s", spinner="dots"
        ) as status:
            restore_task = asyncio.create_task(task)
            while not restore_task.done():
                elapsed = int(time.time() - start)
                status.update(
                    f"[bold]Restoring (pg_restore running)...[/bold] {elapsed}s"
                )
                await asyncio.sleep(0.5)
            return await restore_task  # propagate exceptions

    asyncio.run(_run_with_heartbeat())

    typer.echo(f'Restored "{target_db}" from {dump_path}')


cli.command("s3-bucket-migration")(s3_bucket_migration)
