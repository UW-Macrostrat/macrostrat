import datetime
import sys
import time
from pathlib import Path

from psycopg2.extensions import AsIs
from psycopg2.sql import SQL, Identifier
from rich import print

from ..database import db
from ..utils import MapInfo

__here__ = Path(__file__).parent


def match_strat_names(map: MapInfo):
    """
    Match a given map source's `strat_name` field to Macrostrat strat_name_ids.
    Populates the table maps.map_strat_names
    """

    # Time the process
    start_time = time.time()
    source_id = map.id

    # Find scale table

    print("      Starting strat name match at ", str(datetime.datetime.now()))

    db.run_sql(
        __here__ / "procedures" / "prepare-match-strat-names.sql",
        {"source_id": source_id},
    )

    elapsed = int(time.time() - start_time)
    print(
        "        Done preparing temp tables in ",
        elapsed / 60,
        " minutes and ",
        elapsed % 60,
        " seconds",
    )

    # Time the process
    start_time = time.time()

    # strict time - strict space - strict name
    a = run_match_query(db, True, True, True)

    # strict time - fuzzy space - strict name
    b = run_match_query(db, True, False, True)

    # fuzzy time - strict space - strict name
    c = run_match_query(db, False, True, True)

    # fuzzy time - fuzzy space - strict name
    d = run_match_query(db, False, False, True)

    # no time - strict space - strict name
    e = run_match_query(db, None, True, True)

    # no time - fuzzy space - strict name
    f = run_match_query(db, None, False, True)

    # strict time - strict space - fuzzy name
    g = run_match_query(db, True, True, False)

    # strict time - fuzzy space - fuzzy name
    h = run_match_query(db, True, False, False)

    # fuzzy time - strict space - fuzzy name
    i = run_match_query(db, False, True, False)

    # fuzzy time - fuzzy space - fuzzy name
    j = run_match_query(db, False, False, False)

    # no time - strict space - fuzzy name
    k = run_match_query(db, None, True, False)

    # no time - fuzzy space - fuzzy name
    l = run_match_query(db, None, False, False)

    elapsed = int(time.time() - start_time)
    print(
        "        Done with matching in ",
        elapsed / 60,
        " minutes and ",
        elapsed % 60,
        " seconds",
    )


def describe_argument(match_type: bool | None):
    if match_type == True:
        return "strict"
    elif match_type == False:
        return "fuzzy"
    else:
        return "no"


def run_match_query(db, strict_time, strict_space, strict_name):
    time = describe_argument(strict_time)
    space = describe_argument(strict_space)
    name = describe_argument(strict_name)

    print(
        f"{time} time, {space} space, {name} name",
    )

    match_type = "strat_name"

    if not strict_name:
        match_type += "_fname"

    if not strict_space:
        match_type += "_fspace"

    if strict_time == False:
        match_type += "_ftime"
    elif strict_time == None:
        match_type += "_ntime"

    macroNameMatch = "rank_name" if strict_name else "name_no_lith"
    mapNameMatch = "strat_name" if strict_name else "strat_name_clean"

    # Relax the matching constraints
    space_buffer = 0 if strict_space else 1.2

    # Time buffer
    time_fuzz = 0 if strict_time else 25

    where_clause = "WHERE lsn.strat_name_id = snft.strat_name_id"

    if strict_time is not None:
        where_clause += """ AND ((lsn.late_age) < (intervals_bottom.age_bottom + :time_fuzz))
            AND ((lsn.early_age) > (intervals_top.age_top - :time_fuzz))"""

    query = """
        INSERT INTO maps.map_strat_names
        SELECT unnest(map_ids), lsn.strat_name_id, :match_type
        FROM temp_rocks tr
        JOIN temp_names lsn
          ON {macro_name_match} = {map_name_match}
        JOIN macrostrat.strat_name_footprints snft
          ON ST_Intersects(ST_Buffer(snft.geom, :buffer_amount), ST_Buffer(tr.envelope, :buffer_amount))
        JOIN macrostrat.intervals intervals_top on tr.t_interval = intervals_top.id
        JOIN macrostrat.intervals intervals_bottom on tr.b_interval = intervals_bottom.id
        {where_clause}
    """

    # Handle no time in the query!!!
    db.run_sql(
        query,
        {
            "match_type": match_type,
            "where_clause": SQL(where_clause),
            "time_fuzz": time_fuzz,
            "buffer_amount": space_buffer,
            "macro_name_match": Identifier("lsn", macroNameMatch),
            "map_name_match": Identifier("tr", mapNameMatch),
        },
    )
