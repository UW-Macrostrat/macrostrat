import os

os.environ["USE_PYGEOS"] = "0"

from sys import stdin

from psycopg2.sql import Identifier
from typer import Option

from macrostrat.core import app
from macrostrat.database import Database
from macrostrat.map_integration.commands.prepare_fields import _prepare_fields
from macrostrat.map_integration.pipeline import ingest_map
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.file_discovery import find_gis_files
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_integration.custom_integrations.japan_full_map import japan_full_map

from . import pipeline
from .commands.copy_sources import copy_macrostrat_sources
from .commands.fix_geometries import fix_geometries
from .commands.ingest import ingest_map
from .commands.prepare_fields import prepare_fields
from .commands.set_srid import apply_srid
from .commands.source_info import source_info
from .commands.sources import map_sources
from .database import get_database
from .migrations import run_migrations
from .process import cli as _process
from .process.insert import _delete_map_data
from .utils import IngestionCLI, MapInfo, table_exists

help_text = f"""Ingest maps into Macrostrat.

Active map: [bold cyan]{app.state.get("active_map")}[/]
"""

cli = IngestionCLI(no_args_is_help=True, name="map-ingestion", help=help_text)


@cli.command(name="set-active")
def set_active_map(map: MapInfo = None):
    """Set the active map for the current session."""
    if map is None:
        app.console.print("Clearing active map")
    else:
        app.console.print(f"Setting active map to [item]{map.slug}")
    app.state.set("active_map", map.slug)


cli.add_command(ingest_map, name="ingest")
cli.add_command(prepare_fields, name="prepare-fields")
cli.add_command(fix_geometries, name="fix-geometries")
cli.add_command(apply_srid, name="apply-srid")

_pipeline = IngestionCLI(
    no_args_is_help=True, help="Ingest map data from archive files."
)
_pipeline.add_command(pipeline.upload_file, name="upload-file")
_pipeline.add_command(pipeline.ingest_slug, name="ingest-map")
_pipeline.add_command(pipeline.ingest_csv, name="ingest-csv")
_pipeline.add_command(
    pipeline.run_polling_loop, name="run-polling-loop", rich_help_panel="Daemons"
)
_pipeline.add_command(
    pipeline.create_slug, name="init-map", rich_help_panel="Low-level"
)
cli.add_typer(_pipeline, name="pipeline")

cli.add_typer(_process, name="process")

cli.add_command(source_info, name="info")


sources = IngestionCLI(no_args_is_help=True)
sources.add_command(copy_macrostrat_sources, name="copy")
sources.add_command(map_sources, name="list")


@sources.command(name="delete")
def delete_sources(
    slugs: list[str],
    dry_run: bool = Option(False, "--dry-run"),
    all_data: bool = Option(False, "--all-data"),
):
    """Delete sources from the map ingestion database."""
    db = get_database()

    if not stdin.isatty() and len(slugs) == 1 and slugs[0] == "-":
        slugs = [line.strip() for line in stdin]

    if dry_run:
        print("Deleting maps:")
        print("  " + "\n  ".join(slugs))

        print("\nDry run; not actually deleting anything")
        return

    for slug in slugs:
        print(f"Deleting map {slug}")
        print(slug)
        tables = db.run_query(
            "SELECT primary_table, primary_line_table FROM maps.sources WHERE slug = :slug",
            dict(slug=slug),
        ).fetchone()

        line_table = None
        poly_table = None
        if tables is not None:
            line_table = tables.primary_line_table
            poly_table = tables.primary_table

        if line_table is None:
            line_table = f"{slug}_lines"
        if poly_table is None:
            poly_table = f"{slug}_polygons"
        points_table = f"{slug}_points"

        for table in [line_table, poly_table, points_table]:
            db.run_sql(
                "DROP TABLE IF EXISTS {table}",
                dict(table=Identifier("sources", table)),
            )

        ingest_process = db.run_query(
            """
            SELECT id FROM maps_metadata.ingest_process
            JOIN maps.sources ON maps.sources.source_id = maps_metadata.ingest_process.source_id
            WHERE maps.sources.slug = :slug
            """,
            dict(slug=slug),
        ).fetchone()

        if ingest_process:
            ingest_process_id = ingest_process[0]

            print("Ingest Process ID", ingest_process_id)

            db.run_sql(
                "DELETE FROM maps_metadata.ingest_process_tag WHERE ingest_process_id = :ingest_process_id",
                dict(ingest_process_id=ingest_process_id),
            )
            db.run_sql(
                "DELETE FROM maps_metadata.ingest_process WHERE id = :ingest_process_id",
                dict(ingest_process_id=ingest_process_id),
            )

        source_id = db.run_query(
            "SELECT source_id FROM maps.sources WHERE slug = :slug",
            dict(slug=slug),
        ).scalar()
        if all_data:
            _delete_map_data(source_id)

        db.run_sql("DELETE FROM maps.sources WHERE slug = :slug", dict(slug=slug))


@cli.command(name="change-slug")
def change_slug(map: MapInfo, new_slug: str, dry_run: bool = False):
    """Change a map's slug."""

    db = get_database()

    # Normalize the new slug
    new_slug = new_slug.lower().replace(" ", "_").replace("_", "-")

    if new_slug == map.slug:
        return

    print(f"Changing slug for map {map.id} from {map.slug} to {new_slug}")

    # Check that the new slug is not already in use
    existing = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=new_slug),
    ).fetchone()
    if existing is not None:
        raise ValueError(f"Slug {new_slug} already in use")

    with db.transaction():
        # Change sources table names
        for table in ["polygons", "lines", "points"]:
            # Check if the table exists
            if not table_exists(db, f"{map.slug}_{table}", schema="sources"):
                continue

            if dry_run:
                print(f"Would rename {map.slug}_{table} to {new_slug}_{table}")
                continue
            old_table = f"{map.slug}_{table}"
            new_table = f"{new_slug}_{table}"
            db.run_query(
                "ALTER TABLE {old_table} RENAME TO {new_table}",
                dict(
                    old_table=Identifier("sources", old_table),
                    new_table=Identifier(new_table),
                ),
            )

        if dry_run:
            return

        db.run_query(
            "UPDATE maps.sources SET slug = :new_slug WHERE source_id = :source_id",
            dict(new_slug=new_slug, source_id=map.id),
        )
        db.session.commit()
        print(f"Changed slug from {map.slug} to {new_slug}")


@cli.command(name="update-status")
def update_status():
    """Update the status of all maps."""
    from .status import update_status_for_all_maps

    db = get_database()

    update_status_for_all_maps(db)


# TODO: integrate this migration command with the main database migrations
def _run_migrations(database: str = None):
    """Run migrations to convert a Macrostrat v1 sources table to v2 format."""
    db = get_database()

    database_url = db.engine.url
    _db = db
    if database is not None:
        if database.startswith("postgres") and "//" in database:
            database_url = database
        else:
            database_url = database_url.set(database=database)
        _db = Database(database_url)

    print(f"Running migrations on {database_url}")

    run_migrations(_db)


sources.add_command(_run_migrations, name="migrate-schema")

cli.add_typer(sources, name="sources", help="Manage map sources")

# ______________________________________________________________________________________________________________________

from pathlib import Path

from macrostrat.map_integration.utils.file_discovery import find_gis_files


@cli.command(name="staging")
def staging(
    slug: str,
    data_path: str,
    name: str,
    legend_file: str = Option(None, help="metadata URL to merge into the sources polygons/lines/points table"),
    legend_key: str = Option(None, help="primary key to left join the metadata into the sources polygons/lines/points table"),
    legend_table: str = Option("polygons", help="Options: polygons, lines, or points. specifies the table in which the legend metadata is merged into. It defaults to sources polygons"),
    filter: str = Option(None, help="Filter applied to GIS file selection"),
):
    """
    Ingest a map, update metadata, prepare fields, and build geometries.
    """
    db = get_database()
    print(f"Ingesting {slug} from {data_path}")

    gis_files, excluded_files = find_gis_files(Path(data_path), filter=filter)
    if not gis_files:
        raise ValueError(f"No GIS files found in {data_path}")

    print(f"Found {len(gis_files)} GIS file(s)")
    for path in gis_files:
        print(f"  ✓ {path}")

    if excluded_files:
        print(f"Excluded {len(excluded_files)} file(s) due to filter:")
        for path in excluded_files:
            print(f"  ⚠️ {path}")

    #add preprocess
    # ingest the map!

    """ Example data_preprocess command:
    macrostrat maps staging japan_full_map \
    /Users/afromandi/Macrostrat/Maps/Japan/Japan\ Full \
    "Japan" \
    --data-preprocess-url /Users/afromandi/Macrostrat/Maps/Japan/Japan\ Full/legend.tsv \
    --data-preprocess-key symbol"""
    ingest_map(slug, gis_files, if_exists="replace", legend_file=legend_file, legend_key=legend_key, legend_table=legend_table)

    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    if source_id is None:
        raise RuntimeError(f"Could not find source for slug {slug}")

    if name:
        db.run_sql(
            "UPDATE maps.sources SET name = :name WHERE source_id = :source_id",
            dict(name=name, source_id=source_id),
        )

    db.run_sql(
        "UPDATE maps.sources SET scale = :scale WHERE source_id = :source_id",
        dict(scale="large", source_id=source_id),
    )

    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process (state, source_id, object_group_id)
        VALUES (:state, :source_id, :object_group_id);
        """,
        dict(state="ingested", source_id=source_id, object_group_id=1),
    )

    map_info = get_map_info(db, slug)

    _prepare_fields(map_info)
    create_rgeom(map_info)
    create_webgeom(map_info)

    # Metadata assertions
    row = db.run_query(
        "SELECT name, scale FROM maps.sources WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    print(row)

    # Ingest process assertions
    ingest_process = db.run_query(
        "SELECT source_id, object_group_id, state FROM maps_metadata.ingest_process WHERE source_id = :source_id",
        dict(source_id=source_id),
    ).fetchone()
    print(ingest_process)

    # Data exists
    count = db.run_query(f"SELECT COUNT(*) FROM sources.{slug}_polygons").scalar()
    print(count)

    # Geometry column assertions
    rgeom = db.run_query(
        """
        SELECT rgeom FROM maps.sources WHERE slug = :slug
        """,
        dict(slug=slug),
    ).fetchone()
    print(rgeom)

    web_geom = db.run_query(
        """
        SELECT web_geom FROM maps.sources WHERE slug = :slug
        """,
        dict(slug=slug),
    ).fetchone()
    print(web_geom)

    if any(val is None for val in [row, ingest_process, rgeom, web_geom]):
        raise RuntimeError("Staging failed: Some expected records were not inserted.")

    print(
        f"\nFinished staging setup for {slug}. View map here: https://dev2.macrostrat.org/maps/ingestion/{source_id}/ \n"
    )


#----------------------------------------------------------------------------------------------------------------------


@cli.command(name="staging-bulk")
def staging_bulk(
    parent_path: str = Option(..., help="Parent directory containing region subfolders"),
    prefix: str = Option(..., help="Slug prefix to avoid collisions"),
    filter: str = Option(None, help="Filter applied to GIS file selection"),
):
    """
    Ingest all maps from subdirectories within a parent folder.
    """
    db = get_database()
    parent = Path(parent_path)

    if not parent.exists() or not parent.is_dir():
        raise ValueError(f"{parent_path} is not a valid directory.")

    region_dirs = sorted([p for p in parent.iterdir() if p.is_dir()])

    for region_path in region_dirs:
        slug = f"{region_path.name.lower()}_{prefix}"
        name = region_path.name
        data_path = region_path
        print(f"\n🚀 Ingesting {slug} from {data_path}")

        gis_files, excluded_files = find_gis_files(data_path, filter=filter)
        if not gis_files:
            print(f"⚠️ No GIS files found in {data_path}, skipping.")
            continue
        for path in gis_files:
            print(f"  ✓ {path}")
        ingest_map(slug, gis_files, if_exists="replace")

        source_id = db.run_query(
            "SELECT source_id FROM maps.sources WHERE slug = :slug",
            dict(slug=slug),
        ).scalar()

        if source_id is None:
            raise RuntimeError(f"Could not find source for slug {slug}")

        if name:
            db.run_sql(
                "UPDATE maps.sources SET name = :name WHERE source_id = :source_id",
                dict(name=name, source_id=source_id),
            )

        db.run_sql(
            "UPDATE maps.sources SET scale = :scale WHERE source_id = :source_id",
            dict(scale="large", source_id=source_id),
        )

        db.run_sql(
            """
            INSERT INTO maps_metadata.ingest_process (state, source_id, object_group_id)
            VALUES (:state, :source_id, :object_group_id);
            """,
            dict(state="ingested", source_id=source_id, object_group_id=1),
        )

        map_info = get_map_info(db, slug)
        _prepare_fields(map_info)
        create_rgeom(map_info)
        create_webgeom(map_info)

        # Metadata assertions
        row = db.run_query(
            "SELECT name, scale FROM maps.sources WHERE source_id = :source_id",
            dict(source_id=source_id),
        ).fetchone()
        print(row)

        # Ingest process assertions
        ingest_process = db.run_query(
            "SELECT source_id, object_group_id, state FROM maps_metadata.ingest_process WHERE source_id = :source_id",
            dict(source_id=source_id),
        ).fetchone()
        print(ingest_process)

        # Data exists
        count = db.run_query(f"SELECT COUNT(*) FROM sources.{slug}_polygons").scalar()
        print(count)

        # Geometry column assertions
        rgeom = db.run_query(
            """
            SELECT rgeom FROM maps.sources WHERE slug = :slug
            """,
            dict(slug=slug),
        ).fetchone()
        print(rgeom)

        web_geom = db.run_query(
            """
            SELECT web_geom FROM maps.sources WHERE slug = :slug
            """,
            dict(slug=slug),
        ).fetchone()
        print(web_geom)

        if any(val is None for val in [row, ingest_process, rgeom, web_geom]):
            raise RuntimeError("Staging failed: Some expected records were not inserted.")

        print(
            f"\nFinished staging setup for {slug}. View map here: https://dev2.macrostrat.org/maps/ingestion/{source_id}/ \n"
        )