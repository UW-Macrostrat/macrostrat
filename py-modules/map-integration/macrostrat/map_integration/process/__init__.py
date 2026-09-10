"""
Map processing pipeline (v2)

+ macrostrat process rgeom <source_id>
+ macrostrat process web_geom <source_id>
+ macrostrat process legend <source_id>
+ macrostrat match strat_names <source_id>
+ macrostrat match units <source_id>
+ macrostrat match liths <source_id>
+ macrostrat process burwell_lookup <source_id>
+ macrostrat process legend_lookup <source_id>
+ macrostrat process carto <source_id>
+ macrostrat process carto_lines <source_id>
+ macrostrat seed <source_id>

"""

from typing import Annotated, Optional

from rich import print
from typer import Option

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..utils import IngestionCLI
from ..utils.map_info import (
    MapInfo,
    MapSelector,
    has_map_schema_data,
    resolve_maps,
)
from .extract_strat_name_candidates import extract_strat_name_candidates
from .geometry import create_rgeom, create_webgeom
from .insert import copy_to_maps, run_insert
from .legend_lookup import legend_lookup
from .lookup import make_lookup
from .status import processing_status

cli = IngestionCLI(
    no_args_is_help=True, name="process", help="Process map data once ingested"
)

cli.add_command(processing_status, name="status")


def for_each_map(selectors, step, **kwargs):
    """Run a single-map processing step over every selected map.

    Every step in this module takes a `MapInfo` first and options after, so one
    adapter covers all of them. Failures are collected rather than aborting the
    sweep: over 114 maps, stopping on the first bad one wastes the rest of the
    run, and the summary says which to look at.
    """
    db = get_database()
    maps = resolve_maps(db, selectors)
    many = len(maps) > 1
    if many:
        print(f"[dim]{len(maps)} maps[/]")

    failed = []
    for m in maps:
        if many:
            print(f"[bold cyan]{m.slug}[/] [dim]#{m.id}[/]")
        try:
            step(m, **kwargs)
        except Exception as err:  # noqa: BLE001 -- reported per map, see above
            if not many:
                raise
            failed.append((m.slug, str(err).strip().splitlines()[0]))
            print(f"  [red]failed[/] {failed[-1][1]}")

    if failed:
        print(f"\n[red]{len(failed)} of {len(maps)} failed[/]")
        for slug, err in failed:
            print(f"  [red]{slug}[/] {err}")
        raise MacrostratError(f"{len(failed)} maps failed")


def run_pipeline(source: MapInfo, delete_existing: bool = False, scale: str = None):
    """Run the full post-ingestion pipeline for one map source."""
    try:
        copy_to_maps(
            get_database(), source, delete_existing=delete_existing, scale=scale
        )
    except ValueError as e:
        print(e)
        if not delete_existing:
            print("Continuing with existing map data")
    run_legend(source)
    match_strat_names(source)
    match_units(source)
    match_liths(source)
    make_lookup(source)
    legend_lookup(source)
    finalize_one(source)


@cli.command(name="pipeline")
def pipeline(maps: MapSelector, delete_existing: bool = False, scale: str = None):
    """
    Run the full post-pipeline for the selected map sources

    This includes:
    - Copy to maps schema
    - Legend lookup table generation
    - Match strat names
    - Match units
    - Match liths
    - Make lookup
    """
    for_each_map(maps, run_pipeline, delete_existing=delete_existing, scale=scale)


def run_legend(map: MapInfo):
    """Update legend lookup tables for one map source."""
    db = get_database()
    proc = sql_file("update-legend")
    db.run_sql(proc, {"source_id": map.id})


@cli.command(name="rgeom", rich_help_panel="Sources")
def rgeom(maps: MapSelector):
    """Compose reference geometries for the selected map sources."""
    for_each_map(maps, create_rgeom)


@cli.command(name="web-geom", rich_help_panel="Sources")
def web_geom(maps: MapSelector, legacy: bool = False):
    """Create simplified web geometries for the selected map sources."""
    for_each_map(maps, create_webgeom, legacy=legacy)


@cli.command(name="extract-strat-names", rich_help_panel="Sources")
def extract_strat_names(
    maps: MapSelector,
    field: str = Option(
        None,
        help="The field to extract from. Defaults to a concatenation of all text fields.",
    ),
    use_sources: bool = Option(False, help="Operate in the sources schema"),
):
    """Extract stratigraphic name candidates for the selected map sources."""
    for_each_map(
        maps, extract_strat_name_candidates, field=field, use_sources=use_sources
    )


@cli.command(name="insert", rich_help_panel="Map")
def insert(
    maps: MapSelector,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: Annotated[
        Optional[str],
        Option(
            "--staging-prefix",
            help="Name the sources.<prefix>_* staging tables (default: the slug)",
        ),
    ] = None,
    allow_unattributed: Annotated[
        bool,
        Option(
            "--allow-unattributed",
            help="Insert even though lith/t_interval/b_interval are entirely null",
        ),
    ] = False,
):
    """Copy staged data to the maps schema for the selected map sources.

    A compilation whose members share one staging table passes it once:
    `insert 'ngs-*' --staging-prefix ngs` covers all 114.
    """
    for_each_map(
        maps,
        run_insert,
        delete_existing=delete_existing,
        scale=scale,
        staging_prefix=staging_prefix,
        allow_unattributed=allow_unattributed,
    )


@cli.command(name="legend", rich_help_panel="Map")
def legend(maps: MapSelector):
    """Update legend lookup tables for the selected map sources."""
    for_each_map(maps, run_legend)


@cli.command(name="strat-names", rich_help_panel="Matching")
def strat_names(maps: MapSelector):
    """Match the selected map sources to Macrostrat stratigraphic names."""
    for_each_map(maps, match_strat_names)


@cli.command(name="units", rich_help_panel="Matching")
def units(maps: MapSelector):
    """Match the selected map sources to Macrostrat units."""
    for_each_map(maps, match_units)


@cli.command(name="liths", rich_help_panel="Matching")
def liths(maps: MapSelector):
    """Match the selected map sources to Macrostrat lithologies."""
    for_each_map(maps, match_liths)


@cli.command(name="lookup", rich_help_panel="Lookup")
def lookup(maps: MapSelector):
    """Refresh the lookup tables for the selected map sources."""
    for_each_map(maps, make_lookup)


@cli.command(name="legend-lookup", rich_help_panel="Lookup")
def legend_lookup_cmd(maps: MapSelector):
    """Refresh legend lookup tables for the selected map sources."""
    for_each_map(maps, legend_lookup)


@cli.command(name="finalize", rich_help_panel="Map")
def finalize(maps: MapSelector):
    """Finalize the selected map sources."""
    for_each_map(maps, finalize_one)


def finalize_one(map: MapInfo):
    """
    Finalize a map source by setting is_finalized to True in the sources table.

    This is a computed parameter, so we can change its design in the future.
    """
    db = get_database()
    is_finalized = has_map_schema_data(db, map)

    if is_finalized:
        set_finalized(map)
        print(f"Map {map.id} {map.slug} is finalized")
    else:
        raise MacrostratError(
            f"Map {map.id} {map.slug} has no data in the [cyan]maps[/cyan] schema"
        )


def set_finalized(map: MapInfo):
    """
    Set a map source as finalized
    """
    db = get_database()
    db.run_query(
        "UPDATE maps.sources SET is_finalized = TRUE WHERE source_id = :map_id",
        dict(map_id=map.id),
    )
    db.session.commit()
