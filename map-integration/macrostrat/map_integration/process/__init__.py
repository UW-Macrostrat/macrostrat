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
from ..utils import IngestionCLI
from .geometry import create_rgeom, create_webgeom
from .status import processing_status

app = IngestionCLI(no_args_is_help=True, name="process")

app.add_command(processing_status, name="status")

app.add_command(create_rgeom, name="rgeom", rich_help_panel="Steps")
app.add_command(create_webgeom, name="web-geom", rich_help_panel="Steps")
