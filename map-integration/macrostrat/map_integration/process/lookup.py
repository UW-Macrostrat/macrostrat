import sys

from psycopg2.extensions import AsIs
from psycopg2.sql import Identifier

from ..database import LegacyCommandBase, sql_file
from ..utils import MapInfo


def make_lookup(source: MapInfo):
    """
    Inserts/updates a given map source's records in public.lookup_<scale>
    Computes things like best_age_top/bottom and the appropriate color for each polygon
    """
    Lookup().run(source_id=source.id)


class Lookup(LegacyCommandBase):

    UNDER = {"small": "tiny", "medium": "small", "large": "medium"}
    scaleIsIn = {
        "tiny": ["tiny"],
        "small": ["small", "medium"],
        "medium": ["small", "medium", "large"],
        "large": ["large"],
    }

    source_id = None

    def source_stats(self):
        self.pg["cursor"].execute(
            """
          SELECT primary_table FROM maps.sources WHERE source_id = %(source_id)s
        """,
            {"source_id": self.source_id},
        )
        primary_table = self.pg["cursor"].fetchone().primary_table

        self.pg["cursor"].execute(
            """
          WITH second AS (
            SELECT ST_MakeValid(geom) geom FROM sources."%(primary_table)s"
          ),
          third AS (
            SELECT round(sum(ST_Area(geom::geography)*0.000001)) area, COUNT(*) features
            FROM second
          )
          UPDATE maps.sources AS a
          SET area = s.area, features = s.features
          FROM third AS s
          WHERE a.source_id = %(source_id)s;

          UPDATE maps.sources
          SET display_scales = ARRAY[scale]
          WHERE source_id = %(source_id)s;
        """,
            {"primary_table": AsIs(primary_table), "source_id": self.source_id},
        )
        self.pg["connection"].commit()

    def refresh(self):
        # Delete source from lookup_scale
        self.pg["cursor"].execute(
            """
            DELETE FROM lookup_%s
            WHERE map_id IN (
                SELECT map_id
                FROM maps.%s
                WHERE source_id = %s
            )
        """,
            (AsIs(self.scale), AsIs(self.scale), self.source_id),
        )
        proc = sql_file("build-lookup-table")
        # Insert source into lookup_scale
        self.pg["cursor"].execute(
            proc,
            {"scale": AsIs(self.scale), "source_id": self.source_id},
        )
        self.pg["connection"].commit()

        self.source_stats()

        # source_stats(cursor, connection, source_id)

    def run(self, source_id):
        self.pg["cursor"].execute(
            """
            SELECT scale
            FROM maps.sources
            WHERE source_id = %(source_id)s
        """,
            {"source_id": source_id},
        )
        scale = self.pg["cursor"].fetchone()

        if scale is None:
            print("Source ID %s was not found in maps.sources" % (source_id,))
            sys.exit(1)

        if scale.scale is None:
            print("Source ID %s is missing a scale" % (source_id,))
            sys.exit(1)

        self.source_id = source_id
        self.scale = scale.scale

        self.refresh()
