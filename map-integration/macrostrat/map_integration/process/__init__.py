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

from ..database import db, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..utils import IngestionCLI
from ..utils.map_info import MapInfo
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
    copy_to_maps(source, delete_existing=delete_existing, scale=scale)
    legend(source)
    match_strat_names(source)
    match_units(source)
    match_liths(source)
    make_lookup(source)
    # legend_lookup(source)


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
    proc = sql_file("update-legend")
    db.run_sql(proc, {"source_id": map.id})


cli.add_command(match_strat_names, name="strat-names", rich_help_panel="Matching")
cli.add_command(match_units, name="units", rich_help_panel="Matching")
cli.add_command(match_liths, name="liths", rich_help_panel="Matching")

cli.add_command(make_lookup, name="lookup", rich_help_panel="Lookup")
cli.add_command(legend_lookup, name="legend-lookup", rich_help_panel="Lookup")
