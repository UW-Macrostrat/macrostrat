from ..base import Base
import sys


class WebGeom(Base):
    """
    macrostrat process web_geom <source_id>:
        Populate the field `web_geom` in the table maps.sources. The web_geom is
        simply the envelope of the given source, but processed so that it renders
        properly on an interactive map (sensibly crosses the dateline). It is
        primarily used for displaying the index map of sources at /map/sources

    Usage:
      macrostrat process web_geom <source_id>
      macrostrat process web_geom -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat process web_geom 123
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    meta = {
        "mariadb": False,
        "pg": True,
        "usage": """
            Populates the field `web_geom` for a given geologic map source.
        """,
        "required_args": {"source_id": "A valid source_id"},
    }

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def run(self, source_id):
        if len(source_id) == 0 or source_id[0] == "--help" or source_id[0] == "-h":
            print(WebGeom.__doc__)
            sys.exit()

        source_id = source_id[0]

        # Get the primary table of the target source
        self.pg["cursor"].execute(
            """
            WITH first as (
                SELECT source_id, (ST_Dump(ST_Split(ST_SetSRID(rgeom, 4326), ST_SetSRID(ST_MakeLine(ST_MakePoint(-180, 90), ST_MakePoint(-180, -90)), 4326)))).geom
                FROM maps.sources
                WHERE source_id = %(source_id)s
            ),

            sides AS (
                SELECT source_id,
                    CASE
                        WHEN ST_XMin(geom) < 0
                            THEN 'w'
                        ELSE 'e'
                     END as side
                     , ST_Area(geom) AS area, geom
                FROM first
                WHERE ST_Area(geom) > 0.01
            ),

            best_sides AS (
                SELECT source_id, side AS best_side, sum(area)
                FROM sides
                GROUP BY source_id, side
                ORDER BY sum desc
                LIMIT 1
            ),

            final AS(
                SELECT sides.source_id,
                    CASE
                        WHEN side = best_side
                            THEN geom
                        WHEN side = 'e' AND best_side = 'w'
                            THEN ST_Translate(geom, -360, 0)
                        WHEN side = 'w' AND best_side = 'e'
                            THEN ST_Translate(geom, 360, 0)
                        END as geom
                FROM sides
                JOIN best_sides ON sides.source_id = best_sides.source_id
            )

            UPDATE maps.sources
            SET web_geom = (
                SELECT
                    ST_MakeEnvelope(
                        st_xmin(ST_Collect(geom)),
                        st_ymin(ST_Collect(geom)),
                        st_xmax(ST_Collect(geom)),
                        st_ymax(ST_Collect(geom)),
                        4326
                )
             FROM final
             GROUP BY source_id
            )
            WHERE source_id = %(source_id)s;
        """,
            {"source_id": source_id},
        )
        self.pg["connection"].commit()
