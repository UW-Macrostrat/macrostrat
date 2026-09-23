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

from functools import partial
from typing import Annotated, Optional

from rich import print
from typer import Argument, Option

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..match.utils import SourceNotMaterialized
from ..utils import IngestionCLI
from ..utils.map_info import (
    MapInfo,
    MapSelector,
    has_map_schema_data,
    resolve_maps,
)
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

    # A source with no polygons of its own has nothing for these steps to do.
    # Compilations are the usual case -- their content is their members' -- and
    # a registered but uncopied source is the other. Neither is a failure, and
    # reporting them as one buried the real ones.
    skip_empty_maps = kwargs.pop("skip_empty_maps", True)

    materialized = set(
        db.run_query(
            """
            SELECT DISTINCT source_id FROM maps.polygons
            WHERE source_id = ANY(CAST(:ids AS integer[]))
            """,
            {"ids": [m.id for m in maps]},
        ).scalars()
    )

    failed = []
    skipped = []
    for m in maps:
        if (m.id not in materialized) and skip_empty_maps:
            skipped.append(m.slug)
            if many:
                print(f"[dim]{m.slug} #{m.id} -- no polygons, skipped[/]")
            else:
                raise SourceNotMaterialized(
                    f"Source {m.id} ({m.slug}) has no polygons in any scale table"
                )
            continue
        if many:
            print(f"[bold cyan]{m.slug}[/] [dim]#{m.id}[/]")
        try:
            step(m, **kwargs)
        except Exception as err:  # noqa: BLE001 -- reported per map, see above
            if not many:
                raise
            failed.append((m.slug, str(err).strip().splitlines()[0]))
            print(f"  [red]failed[/] {failed[-1][1]}")

    if skipped:
        print(f"\n[dim]{len(skipped)} of {len(maps)} skipped (no polygons)[/]")
    if failed:
        print(f"\n[red]{len(failed)} of {len(maps)} failed[/]")
        for slug, err in failed:
            print(f"  [red]{slug}[/] {err}")
        raise MacrostratError(f"{len(failed)} maps failed")


def run_pipeline(source: MapInfo, delete_existing: bool = False, scale: str = None):
    """Run the full post-ingestion pipeline for one map source."""
    db = get_database()
    try:
        copy_to_maps(db, source, delete_existing=delete_existing, scale=scale)
    except ValueError as e:
        print(e)
        if not delete_existing:
            print("Continuing with existing map data")
    run_legend(source)
    match_strat_names(db, source)
    match_units(db, source)
    match_liths(db, source)
    make_lookup(db, source)
    legend_lookup(db, source)
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
        skip_empty_maps=False,
    )


@cli.command(name="legend", rich_help_panel="Map")
def legend(maps: MapSelector):
    """Update legend lookup tables for the selected map sources."""
    for_each_map(maps, run_legend)


@cli.command(name="strat-names", rich_help_panel="Matching")
def strat_names(
    maps: MapSelector,
    field: str = Option(None, help="Match only on this legend field (e.g. descrip)"),
):
    """Match the selected map sources to Macrostrat stratigraphic names."""
    db = get_database()
    for_each_map(maps, partial(match_strat_names, db, fields=_match_fields(field)))


@cli.command(name="units", rich_help_panel="Matching")
def units(maps: MapSelector):
    """Match the selected map sources to Macrostrat units."""
    db = get_database()
    for_each_map(maps, partial(match_units, db))


@cli.command(name="liths", rich_help_panel="Matching")
def liths(maps: MapSelector):
    """Match the selected map sources to Macrostrat lithologies."""
    db = get_database()
    for_each_map(maps, partial(match_liths, db))


def _match_fields(field: str | None) -> tuple:
    """Resolve a `--field` option to the tuple of legend columns to read."""
    from ..match.strat_names import FIELD_TIERS

    if field is None:
        return FIELD_TIERS
    if field not in FIELD_TIERS:
        raise MacrostratError(
            f"{field!r} is not a legend text field",
            details="Choose one of: " + ", ".join(FIELD_TIERS),
        )
    return (field,)


@cli.command(name="strat-names-report", rich_help_panel="Matching")
def strat_names_report(
    pattern: str = Argument(..., help="Source slug or SQL LIKE pattern, e.g. `ngs-%`"),
    examples: int = Option(4, help="Lost/gained examples to print per source"),
    field: str = Option(None, help="Match only on this legend field (e.g. descrip)"),
    examples_from: str = Option(
        None,
        "--examples-from",
        help="Show worked examples of matches from this field instead of the"
        " lost/gained lists. Matching is unaffected.",
    ),
    full_text: bool = Option(
        False,
        "--full-text",
        help="Print the whole source text of each example, with the matched"
        " names highlighted. A description match cannot be judged without it.",
    ),
):
    """Score the prototype matcher against what the current pipeline produced.

    Read-only. Writes nothing and touches no pipeline table -- it reports what a
    legend-grain matcher *would* find, beside `maps.legend.strat_name_ids` as it
    stands, so the two can be compared before anything is replaced.
    """
    from ..match.strat_names_report import strat_names_report as report

    report(
        get_database(),
        pattern,
        fields=_match_fields(field),
        examples=examples,
        examples_from=examples_from,
        full_text=full_text,
    )


@cli.command(name="lookup", rich_help_panel="Lookup")
def lookup(maps: MapSelector):
    """Refresh the lookup tables for the selected map sources."""
    db = get_database()
    for_each_map(maps, partial(make_lookup, db))


@cli.command(name="legend-lookup", rich_help_panel="Lookup")
def legend_lookup_cmd(maps: MapSelector):
    """Refresh legend lookup tables for the selected map sources."""
    db = get_database()
    for_each_map(maps, partial(legend_lookup, db))


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
