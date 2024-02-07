import datetime
import sys
import time
from enum import Enum
from pathlib import Path

from psycopg2.extensions import AsIs
from psycopg2.sql import SQL, Identifier
from rich import print

from ..database import db
from ..utils import MapInfo

__here__ = Path(__file__).parent


class MatchType(Enum):
    STRICT = True
    FUZZY = False


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

    prepare_match_strat_names(source_id)

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

    # Run the match queries
    for time_match in [MatchType.STRICT, MatchType.FUZZY, None]:
        for space_match in [MatchType.STRICT, MatchType.FUZZY]:
            for name_match in [MatchType.STRICT, MatchType.FUZZY]:
                run_match_query(db, time_match, space_match, name_match)

    elapsed = int(time.time() - start_time)
    print(
        "        Done with matching in ",
        elapsed / 60,
        " minutes and ",
        elapsed % 60,
        " seconds",
    )


def describe_argument(match_type: MatchType | None):
    if match_type == MatchType.STRICT:
        return "strict"
    elif match_type == MatchType.FUZZY:
        return "fuzzy"
    else:
        return "no"


def prepare_match_strat_names(source_id: int):
    db.run_sql(
        __here__ / "procedures" / "prepare-match-strat-names.sql",
        {"source_id": source_id},
    )


def run_match_query(
    db, time_match: MatchType | None, space_match: MatchType, name_match: MatchType
):
    time = describe_argument(time_match)
    space = describe_argument(space_match)
    name = describe_argument(name_match)

    print(
        f"{time} time, {space} space, {name} name",
    )

    match_type = "strat_name"

    if not name_match:
        match_type += "_fname"

    if not space_match:
        match_type += "_fspace"

    if time_match == MatchType.FUZZY:
        match_type += "_ftime"
    elif time_match is None:
        match_type += "_ntime"

    macroNameMatch = "rank_name" if name_match else "name_no_lith"
    mapNameMatch = "strat_name" if name_match else "strat_name_clean"

    # Relax the matching constraints
    space_buffer = 0 if space_match else 1.2

    # Time buffer
    time_fuzz = 0 if time_match else 25

    where_clause = "WHERE lsn.strat_name_id = snft.strat_name_id"

    if time_match is not None:
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
