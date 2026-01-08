import os
from typing import Required

os.environ["USE_PYGEOS"] = "0"
os.environ["USE_PYGEOS"] = "0"

import re
from pathlib import Path
from sys import stdin

from psycopg2.sql import Identifier
from rich.console import Console
from typer import Option

from macrostrat.core import app
from macrostrat.database import Database
from macrostrat.map_integration.commands.prepare_fields import _prepare_fields
#from macrostrat.map_integration.pipeline import ingest_map
from macrostrat.map_integration.process.geometry import create_rgeom, create_webgeom
from macrostrat.map_integration.utils.ingestion_utils import (
    find_gis_files,
    normalize_slug,
    process_sources_metadata,
)
from macrostrat.map_integration.utils.map_info import get_map_info
from macrostrat.map_integration.utils.s3_file_management import *

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
from .pipeline import upload_file
from .process import cli as _process
from .process.insert import _delete_map_data
from .utils import IngestionCLI, MapInfo, table_exists

help_text = f"""Ingest maps into Macrostrat.

Active map: [bold cyan]{app.state.get("active_map")}[/]
"""
console = Console()
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
    slug: list[str] = Option(
        ...,
        help="BULK delete = filename.txt [every line lists the slug_name to delete. no whitespaces.]\n "
        + "SINGLE delete = 'slug_name' [list the slug_name in quotes]",
    ),
    dry_run: bool = Option(False, "--dry-run"),
    all_data: bool = Option(False, "--all-data"),
):
    """Delete sources from the map ingestion database."""
    db = get_database()

    if not stdin.isatty() and len(slug) == 1 and slug[0] == "-":
        slug = [line.strip() for line in stdin]
    elif len(slug) == 1 and os.path.isfile(slug[0]):
        with open(slug[0]) as file:
            slug = [line.strip() for line in file if line.strip()]

    if dry_run:
        print("Deleting maps:")
        print("  " + "\n  ".join(slug))

        print("\nDry run; not actually deleting anything")
        return

    for s in slug:
        print(f"Deleting map {s}")
        tables = db.run_query(
            "SELECT primary_table, primary_line_table FROM maps.sources WHERE slug = :slug",
            dict(slug=s),
        ).fetchone()

        line_table = None
        poly_table = None
        if tables is not None:
            line_table = tables.primary_line_table
            poly_table = tables.primary_table

        if line_table is None:
            line_table = f"{s}_lines"
        if poly_table is None:
            poly_table = f"{s}_polygons"
        points_table = f"{s}_points"

        for table in [line_table, poly_table, points_table]:
            db.run_sql(
                "DROP TABLE IF EXISTS {table}",
                dict(table=Identifier("sources", table)),
            )

        staging_delete_dir(s, db)

        source_id = db.run_query(
            "SELECT source_id FROM maps.sources WHERE slug = :slug",
            dict(slug=s),
        ).scalar()


        # Delete ALL ingest-related rows for this source
        db.run_sql(
            """
            DELETE FROM maps_metadata.ingest_process_tag
            WHERE ingest_process_id IN (
                SELECT id FROM maps_metadata.ingest_process
                WHERE source_id = :source_id
            )
            """,
            dict(source_id=source_id),
        )

        db.run_sql(
            """
            DELETE FROM maps_metadata.ingest_process
            WHERE source_id = :source_id
            """,
            dict(source_id=source_id),
        )

        if all_data:
            _delete_map_data(source_id)

        db.run_sql("DELETE FROM maps.sources WHERE slug = :slug", dict(slug=s))


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

staging_cli = IngestionCLI(no_args_is_help=True, help="Staging pipeline & storage")
cli.add_typer(staging_cli, name="staging")


def staging(
    data_path: str,
    prefix: str = Option(..., help="Slug region prefix to avoid collisions"),
    pipeline: str = Option("", help="Specify a pipeline to run"),
    merge_key: str = Option(
        "mapunit",
        help="primary key to left join the metadata into the sources polygons/lines/points table",
    ),
    meta_table: str = Option(
        "polygons",
        help="Options: polygons, lines, or points. specifies the table in which the legend metadata is merged into. It defaults to sources polygons",
    ),
    filter: str = Option(None, help="Filter applied to GIS file selection"),
):
    """
    Ingest a map, update metadata, prepare fields, and build geometries.
    """
    db = get_database()

    slug, name, ext = normalize_slug(prefix, Path(data_path))
    # we need to add database insert here.
    print(f"Ingesting {slug} from {data_path}")

    gis_files, excluded_files = find_gis_files(Path(data_path), filter=filter)
    if not gis_files:
        raise ValueError(f"No GIS files found in {data_path}")

    print(f"Found {len(gis_files)} GIS file(s)")
    for path in gis_files:
        print(f"{path}")

    if excluded_files:
        print(f"Excluded {len(excluded_files)} file(s) due to filter:")
        for path in excluded_files:
            print(f"{path}")

    ingest_results = ingest_map(
        slug,
        gis_files,
        pipeline=pipeline,
        if_exists="replace",
        meta_path=data_path,
        merge_key=merge_key,
        meta_table=meta_table,
    )

    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()

    if source_id is None:
        raise RuntimeError(f"Could not find source for slug {slug}")

    # add metadata from AZ map scraper /Users processed_item_urls.csv
    sources_mapping = process_sources_metadata(slug, Path(data_path), None)

    if sources_mapping is not None:
        db.run_sql(
            """
            UPDATE maps.sources
            SET name = :name,
                scale = :scale,
                ingested_by = :ingested_by,
                url = :url,
                ref_title = :ref_title,
                authors = :authors,
                ref_year = :ref_year,
                ref_source = :ref_source,
                isbn_doi = :isbn_doi,
                license = :license,
                keywords = :keywords,
                language = :language,
                description = :description
            WHERE source_id = :source_id
            """,
            dict(
                name=name,
                scale="large",
                ingested_by="macrostrat-admin",
                source_id=source_id,
                url=sources_mapping["url"],
                ref_title=sources_mapping["ref_title"],
                authors=sources_mapping["authors"],
                ref_year=sources_mapping["ref_year"],
                ref_source=sources_mapping["ref_source"],
                isbn_doi=sources_mapping["isbn_doi"],
                license=sources_mapping["license"],
                keywords=sources_mapping["keywords"],  # array
                language=sources_mapping["language"],
                description=sources_mapping["description"],
            ),
        )

    else:
        db.run_sql(
            "UPDATE maps.sources SET name = :name, scale = :scale, ingested_by = :ingested_by WHERE source_id = :source_id",
            dict(
                name=name,
                scale="large",
                ingested_by="macrostrat-admin",
                source_id=source_id,
            ),
        )

    # add map_url later
    db.run_sql(
        """
        INSERT INTO maps_metadata.ingest_process (state, source_id, ingested_by, ingest_pipeline, comments, slug, polygon_state, line_state, point_state)
        VALUES (:state, :source_id, :ingested_by, :ingest_pipeline, :comments, :slug, :polygon_state, :line_state, :point_state);
        """,
        dict(
            state=ingest_results["state"],
            source_id=source_id,
            ingested_by="macrostrat-admin",
            ingest_pipeline=ingest_results["ingest_pipeline"],
            comments=ingest_results["comments"],
            slug=slug,
            polygon_state=ingest_results["polygon_state"],
            line_state=ingest_results["line_state"],
            point_state=ingest_results["point_state"],
        ),
    )

    cmd_upload_dir(slug=slug, data_path=Path(data_path), ext=ext)

    map_info = get_map_info(db, slug)
    _prepare_fields(map_info)
    create_rgeom(map_info)
    create_webgeom(map_info)

    console.print(
        f"[green] \n Finished staging setup for {slug}. "
        f"View map here: https://dev.macrostrat.org/maps/ingestion/{source_id}/ [/green] \n"
    )


staging_cli.add_command(staging, name="ingest")
staging_cli.command("delete")(delete_sources)

# ------------------------------------------
# commands nested under 'macrostrat maps staging...'


@staging_cli.command("s3-upload")
def cmd_upload_dir(slug: str = ..., data_path: Path = ..., ext: str = Option(".gdb", help="extension of the data path"), ingest_process_id: int = Option(None)):
    """Upload a local directory to the staging bucket under SLUG/."""
    db = get_database()
    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug",
        dict(slug=slug),
    ).scalar()
    ingest_id = db.run_query(
        """
        SELECT id
        FROM maps_metadata.ingest_process
        WHERE source_id = :source_id
        ORDER BY id DESC
        LIMIT 1
        """,
        dict(source_id=source_id),
    ).scalar()
    res = staging_upload_dir(slug, data_path, ext, db, ingest_id)
    pretty_res = json.dumps(res, indent=2)
    console.print(f"[green] Processed files \n {pretty_res} [/green]")
    return


@staging_cli.command("s3-delete")
def cmd_delete_dir(
    slug: str = ...,
    file_name: str = Option(
        None, help="deletes a specified file within the slug directory."
    ),
):
    """Delete all objects under SLUG/ in the staging bucket."""
    db = get_database()
    staging_delete_dir(slug, db)
    console.print(
        f"[green] Successfully deleted objects within the s3 bucket under slug: {slug} [/green]"
    )


@staging_cli.command("s3-list")
def cmd_list_dir(
    slug: str = Option(
        ...,
        help="lists all files within a slug directory. Input 'all' to list all the slug directories.",
    ),
    page_token: int = Option(0, "--page-token", "-t", help="Offset to start from"),
    page_size: int = Option(20, "--page-size", "-s", help="Items per page"),
):
    """List paginated files under SLUG."""

    token = page_token
    count = 0
    while True:
        page = staging_list_dir(slug, page_token=token, page_size=page_size)
        for f in page["files"]:
            console.print(f"[blue]{f}[/blue]")
            count += 1

        if page["next_page_token"] is None:
            console.print(f"[green]Total files: {count}[/green]")
            print("\n-- End of list --")
            break
        console.print(f"[green]Scrolled through: {count} files[/green]")

        resp = input("\nPress 'enter' for next page, or 'q' to exit: ").strip().lower()
        if resp in ("exit", "quit", "q"):
            break
        token = page["next_page_token"]


@staging_cli.command("s3-download")
def cmd_download_dir(
    slug: str = ...,
    dest_path: pathlib.Path = Option(
        ..., help="Local destination path to save slug directory to."
    ),
):
    """Download a staging filename_prefix to a local directory."""
    res = staging_download_dir(slug=slug, dest_path=dest_path)
    console.print(f"[green] Download successful![/green]")
    console.print(json.dumps(res, indent=2))


@staging_cli.command("convert-e00")
def convert_e00_to_gpkg(
    data_path: str = Option(..., help="Directory containing .e00 files"),
    slug: str = Option(..., help="Output basename (no .gpkg needed)"),
):
    data_dir = Path(data_path).expanduser().resolve()
    out_gpkg = data_dir / f"{slug}.gpkg"
    e00_files = sorted(data_dir.glob("*.e00"))

    if not e00_files:
        raise ValueError(f"No .e00 files found in {data_dir}")

    def list_layers(e00_path: Path) -> set[str]:
        # ogrinfo output includes lines like: "1: ARC (Line String)"
        p = subprocess.run(
            ["ogrinfo", "-ro", "-so", str(e00_path)],
            capture_output=True,
            text=True,
        )
        text_out = (p.stdout or "") + "\n" + (p.stderr or "")
        layers = set()
        for line in text_out.splitlines():
            line = line.strip()
            # matches: "1: ARC (Line String)"
            if ":" in line and "(" in line:
                left = line.split(":", 1)[1].strip()
                name = left.split("(", 1)[0].strip()
                if name:
                    layers.add(name)
        return layers

    def run(cmd):
        p = subprocess.run(cmd, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr
    created = False
    for f in e00_files:
        base = f.stem
        layers = list_layers(f)
        line_layers = [lyr for lyr in ("ARC",) if lyr in layers]
        point_layers = [lyr for lyr in ("CNT", "LAB", "POINT") if lyr in layers]
        poly_layers = [lyr for lyr in ("PAL", "AREA") if lyr in layers]

        # Lines
        for lyr in line_layers:
            cmd = ["ogr2ogr", "-f", "GPKG"]
            if created:
                cmd += ["-update", "-append"]
            else:
                # create/overwrite first successful write
                cmd += ["-overwrite"]
            cmd += [
                str(out_gpkg), str(f), lyr,
                "-nln", f"{base}_lines",
                "-nlt", "LINESTRING",
            ]
            rc, _, err = run(cmd)
            if rc == 0:
                created = True

        # Points
        for lyr in point_layers:
            if not created:
                cmd = ["ogr2ogr", "-f", "GPKG", "-overwrite"]
            else:
                cmd = ["ogr2ogr", "-f", "GPKG", "-update", "-append"]
            cmd += [
                str(out_gpkg), str(f), lyr,
                "-nln", f"{base}_points",
                "-nlt", "POINT",
            ]
            rc, _, _ = run(cmd)
            if rc == 0:
                created = True

        # Polygons
        for lyr in poly_layers:
            if not created:
                cmd = ["ogr2ogr", "-f", "GPKG", "-overwrite"]
            else:
                cmd = ["ogr2ogr", "-f", "GPKG", "-update", "-append"]
            cmd += [
                str(out_gpkg), str(f), lyr,
                "-nln", f"{base}_polygons",
                "-nlt", "POLYGON",
            ]
            rc, _, _ = run(cmd)
            if rc == 0:
                created = True

        print(f"{f.name}: layers={sorted(layers)}")

    print(f"Done: {out_gpkg}")

# ----------------------------------------------------------------------------------------------------------------------


@staging_cli.command("bulk-ingest")
def staging_bulk(
    data_path: str,
    prefix: str = Option(..., help="Slug filename_prefix to avoid collisions"),
    merge_key: str = Option(
        "mapunit",
        help="primary key to left join the metadata into the sources polygons/lines/points table",
    ),
    meta_table: str = Option(
        "polygons",
        help="Options: polygons, lines, or points. specifies the table in which the metadata is merged into. It defaults to sources polygons",
    ),
    filter: str = Option(None, help="Filter applied to GIS file selection"),
):
    """
    Ingest all maps from subdirectories within a parent folder.
    """
    db = get_database()
    parent = Path(data_path)
    staged_slugs = []
    if not parent.exists() or not parent.is_dir():
        raise ValueError(f"{data_path} is not a valid directory.")

    region_dirs = sorted([p for p in parent.iterdir() if p.is_dir()])

    for region_path in region_dirs:
        slug, name, ext = normalize_slug(prefix, Path(region_path))

        print(f"Ingesting {slug} from {region_path}")
        gis_files, excluded_files = find_gis_files(Path(region_path), filter=filter)
        if not gis_files:
            raise ValueError(f"No GIS files found in {region_path}")

        print(f"Found {len(gis_files)} GIS file(s)")
        for path in gis_files:
            print(f"{path}")

        if excluded_files:
            print(f"Excluded {len(excluded_files)} file(s) due to filter:")
            for path in excluded_files:
                print(f"{path}")

        ingest_results = ingest_map(
            slug,
            gis_files,
            if_exists="replace",
            meta_path=region_path,
            merge_key=merge_key,
            meta_table=meta_table,
        )

        source_id = db.run_query(
            "SELECT source_id FROM maps.sources WHERE slug = :slug",
            dict(slug=slug),
        ).scalar()

        if source_id is None:
            raise RuntimeError(f"Could not find source for slug {slug}")

        # add metadata from AZ map scraper /Users processed_item_urls.csv
        sources_mapping = process_sources_metadata(slug, Path(region_path), parent)

        if sources_mapping is not None:
            db.run_sql(
                """
                UPDATE maps.sources
                SET name = :name,
                    scale = :scale,
                    ingested_by = :ingested_by,
                    url = :url,
                    ref_title = :ref_title,
                    authors = :authors,
                    ref_year = :ref_year,
                    ref_source = :ref_source,
                    isbn_doi = :isbn_doi,
                    license = :license,
                    keywords = :keywords,
                    language = :language,
                    description = :description
                WHERE source_id = :source_id
                """,
                dict(
                    name=name,
                    scale="large",
                    ingested_by="macrostrat-admin",
                    source_id=source_id,
                    url=sources_mapping["url"],
                    ref_title=sources_mapping["ref_title"],
                    authors=sources_mapping["authors"],
                    ref_year=sources_mapping["ref_year"],
                    ref_source=sources_mapping["ref_source"],
                    isbn_doi=sources_mapping["isbn_doi"],
                    license=sources_mapping["license"],
                    keywords=sources_mapping["keywords"],  # array
                    language=sources_mapping["language"],
                    description=sources_mapping["description"],
                ),
            )

        else:
            db.run_sql(
                "UPDATE maps.sources SET name = :name, scale = :scale, ingested_by = :ingested_by WHERE source_id = :source_id",
                dict(
                    name=name,
                    scale="large",
                    ingested_by="macrostrat-admin",
                    source_id=source_id,
                ),
            )

        db.run_sql(
            """
            INSERT INTO maps_metadata.ingest_process (state, source_id, ingested_by, ingest_pipeline, comments, slug, polygon_state, line_state, point_state)
            VALUES (:state, :source_id, :ingested_by, :ingest_pipeline, :comments, :slug, :polygon_state, :line_state, :point_state);
            """,
            dict(
                state=ingest_results["state"],
                source_id=source_id,
                ingested_by="macrostrat-admin",
                ingest_pipeline=ingest_results["ingest_pipeline"],
                comments=ingest_results["comments"],
                slug=slug,
                polygon_state=ingest_results["polygon_state"],
                line_state=ingest_results["line_state"],
                point_state=ingest_results["point_state"],
            ),
        )


        cmd_upload_dir(slug=slug, data_path=region_path, ext=ext)


        map_info = get_map_info(db, slug)
        _prepare_fields(map_info)
        create_rgeom(map_info)
        create_webgeom(map_info)

        print(
            f"\nFinished staging setup for {slug}. View map here: https://dev.macrostrat.org/maps/ingestion/{source_id}/ \n"
        )
    slug_list_path = parent / f"staged_slugs.txt"
    with open(slug_list_path, "w") as file:
        for slug in staged_slugs:
            file.write(slug + "\n")