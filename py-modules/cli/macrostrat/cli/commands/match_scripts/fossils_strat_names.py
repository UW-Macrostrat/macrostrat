import datetime
import sys
import time

from psycopg2.extensions import AsIs
from psycopg2.extras import NamedTupleCursor

from ..base import Base

"""
 select
    coll_strata.lat,
    coll_strata.lng,
    grp,
    formation
from macrostrat.lookup_strat_names, pbdb.coll_strata,pbdb.coll_matrix
where
    coll_strata.collection_no = coll_matrix.collection_no and
    lookup_strat_names.early_age > coll_matrix.late_age and
    lookup_strat_names.late_age < coll_matrix.early_age and
    (formation = strat_name or formation = rank_name or grp=strat_name or grp = rank_name)
into outfile '/Users/sepeters/Public/Drop Box/col.csv' fields terminated by ',' lines terminated by '\n';


remove:
  from all
    .
    ()
    ""

  sanitized
    lith
        ?/s
    upper/lower/middle
    rank
        ?/s
    volcanics

split on
    |
    /
    or
    and
"""


class FossilsStratNames(Base):
    """
    macrostrat match fossils:
        Match Paleobiology Database fossil collections to Macrostrat strat_name_ids.
        Populates the table macrostrat.pbdb_collection_strat_names

    Usage:
      macrostrat match fossils <source_id>
      macrostrat match fossils -h | --help
    Options:
      -h --help                         Show this screen.
      --version                         Show version.
    Examples:
      macrostrat match fossils
    Help:
      For help using this tool, please open an issue on the Github repository:
      https://github.com/UW-Macrostrat/macrostrat-cli
    """

    meta = {
        "mariadb": False,
        "pg": True,
        "usage": """
            Matches Paleobiology Database fossil collections to Macrostrat strat_name_ids
        """,
        "required_args": {},
    }

    source_id = None

    def __init__(self, connections, *args):
        Base.__init__(self, connections, *args)

    def query(self, field, strictTime, strictSpace, strictName):
        print(
            "%s - StrictTime: %s | StrictSpace: %s | StrictName: %s"
            % (field, strictTime, strictSpace, strictName)
        )
        match_type = field
        where = []

        if not strictName:
            match_type += "_fname"

        macroNameMatch = ""
        if strictName:
            macroNameMatch = "lsn.rank_name"
            pbdbNameMatch = "pbdb.%s" % (field,)
        else:
            macroNameMatch = "lower(lsn.name_no_lith)"
            pbdbNameMatch = "pbdb.%s_clean" % (field,)

        where.append(
            "%s = %s"
            % (
                pbdbNameMatch,
                macroNameMatch,
            )
        )

        # Space constraint
        spaceQuery = ""
        if strictSpace == False:
            match_type += "_fspace"
            spaceQuery = (
                "ST_Intersects(ST_Buffer(snf.geom, 1.2), ST_Buffer(pbdb.geom, 1.2))"
            )
        elif strictSpace == None:
            match_type += "_nspace"
            spaceQuery = "true"
        else:
            spaceQuery = "ST_Intersects(snf.geom, pbdb.geom)"

        # Time buffer
        timeFuzz = ""
        if strictTime == False:
            match_type += "_ftime"
            timeFuzz = "25"
        elif strictTime == None:
            match_type += "_ntime"
        else:
            timeFuzz = "0"

        if strictTime != None:
            where.append(
                """((lsn.late_age) < (pbdb.early_age + %s))
                AND ((lsn.early_age) > (pbdb.late_age - %s))
            """
                % (
                    timeFuzz,
                    timeFuzz,
                )
            )

        # Don't match already matched collections
        where.append(
            """
            pbdb.collection_no NOT IN (
                SELECT collection_no
                FROM macrostrat.pbdb_collections_strat_names
            )
        """
        )
        # print self.pg['cursor'].mogrify("""
        #     INSERT INTO macrostrat.pbdb_collections_strat_names (collection_no, strat_name_id, basis_col)
        #     SELECT pbdb.collection_no, lsn.strat_name_id, %(match_type)s
        #     FROM macrostrat.pbdb_collections pbdb
        #     JOIN macrostrat.strat_name_footprints snf ON %(spaceQuery)s
        #     JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = snf.strat_name_id
        #     WHERE %(where)s
        # """, {
        #     'match_type': match_type,
        #     'spaceQuery': AsIs(spaceQuery),
        #     'where': AsIs(' AND '.join(where))
        # })
        self.pg["cursor"].execute(
            """
            INSERT INTO macrostrat.pbdb_collections_strat_names (collection_no, strat_name_id, basis_col)
            SELECT pbdb.collection_no, lsn.strat_name_id, %(match_type)s
            FROM macrostrat.pbdb_collections pbdb
            JOIN macrostrat.strat_name_footprints snf ON %(spaceQuery)s
            JOIN macrostrat.lookup_strat_names lsn ON lsn.strat_name_id = snf.strat_name_id
            WHERE %(where)s
        """,
            {
                "match_type": match_type,
                "spaceQuery": AsIs(spaceQuery),
                "where": AsIs(" AND ".join(where)),
            },
        )
        self.pg["connection"].commit()

    def run(self, source_id):
        if source_id == "--help" or source_id == "-h":
            print(FossilsStratNames.__doc__)
            sys.exit()

        print(
            "      Starting fossil / strat name match at ", str(datetime.datetime.now())
        )

        # Clean up
        self.pg["cursor"].execute(
            """
          DELETE FROM macrostrat.pbdb_collections_strat_names
        """,
            {},
        )
        self.pg["connection"].commit()
        print("        + Done cleaning up")

        fields = ["member", "formation", "grp"]

        # Time the process
        start_time = time.time()

        # strict time - strict space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, True, True, True)

        # strict time - fuzzy space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, True, False, True)

        # fuzzy time - strict space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, False, True, True)

        # fuzzy time - fuzzy space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, False, False, True)

        # no time - strict space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, None, True, True)

        # no time - fuzzy space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, None, False, True)

        # strict time - strict space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, True, True, False)

        # strict time - fuzzy space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, True, False, False)

        # fuzzy time - strict space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, False, True, False)

        # fuzzy time - fuzzy space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, False, False, False)

        # no time - strict space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, None, True, False)

        # no time - fuzzy space - fuzzy name
        for field in fields:
            FossilsStratNames.query(self, field, None, False, False)

        # strict time - no space - strict name
        for field in fields:
            FossilsStratNames.query(self, field, True, None, True)

        elapsed = int(time.time() - start_time)
        print(
            "        Done with in ",
            elapsed / 60,
            " minutes and ",
            elapsed % 60,
            " seconds",
        )
