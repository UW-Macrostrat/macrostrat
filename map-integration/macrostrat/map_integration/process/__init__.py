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

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..utils import IngestionCLI
from ..utils.map_info import MapInfo, has_map_schema_data
from .extract_strat_name_candidates import extract_strat_name_candidates
from .geometry import create_rgeom, create_webgeom
from .insert import copy_to_maps
from .legend_lookup import legend_lookup
from .lookup import make_lookup
from .status import processing_status

cli = IngestionCLI(
    no_args_is_help=True, name="process", help="Process map data once ingested"
)

cli.add_command(processing_status, name="status")


@cli.command(name="pipeline")
def pipeline(source: MapInfo, delete_existing: bool = False, scale: str = None):
    """
    Run the full post-pipeline for a given map source

    This includes:
    - Copy to maps schema
    - Legend lookup table generation
    - Match strat names
    - Match units
    - Match liths
    - Make lookup
    *Legend lookup is ignored because it hangs currently*
    """
    try:
        copy_to_maps(source, delete_existing=delete_existing, scale=scale)
    except ValueError as e:
        print(e)
        if not delete_existing:
            print("Continuing with existing map data")
    legend(source)
    match_strat_names(source)
    match_units(source)
    match_liths(source)
    make_lookup(source)
    legend_lookup(source)
    finalize_map(source)


cli.add_command(create_rgeom, name="rgeom", rich_help_panel="Sources")
cli.add_command(create_webgeom, name="web-geom", rich_help_panel="Sources")
cli.add_command(
    extract_strat_name_candidates, name="extract-strat-names", rich_help_panel="Sources"
)


cli.add_command(copy_to_maps, name="insert", rich_help_panel="Map")


@cli.command(name="legend", rich_help_panel="Map")
def legend(map: MapInfo):
    """
    Update legend lookup tables for a given map source
    """
    db = get_database()
    proc = sql_file("update-legend")
    db.run_sql(proc, {"source_id": map.id})


cli.add_command(match_strat_names, name="strat-names", rich_help_panel="Matching")
cli.add_command(match_units, name="units", rich_help_panel="Matching")
cli.add_command(match_liths, name="liths", rich_help_panel="Matching")

cli.add_command(make_lookup, name="lookup", rich_help_panel="Lookup")
cli.add_command(legend_lookup, name="legend-lookup", rich_help_panel="Lookup")


@cli.command(name="finalize", rich_help_panel="Map")
def finalize_map(map: MapInfo):
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
