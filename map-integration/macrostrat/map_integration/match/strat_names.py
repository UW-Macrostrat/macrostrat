import datetime
import time
from enum import Enum

from psycopg2.sql import SQL, Identifier
from rich import print

from ..database import get_database, sql_file
from ..utils import MapInfo
from .utils import get_match_count


class MatchType(Enum):
    STRICT = True
    FUZZY = False


def match_strat_names(map: MapInfo):
    """
    Match a given map source's `strat_name` field to Macrostrat strat_name_ids.
    Populates the table maps.map_strat_names
    """

    db = get_database()
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

    count = get_match_count(source_id, Identifier("maps", "map_strat_names"))
    print(f"Matched [bold cyan]{count}[/] strat names")


def describe_argument(match_type: MatchType | None):
    if match_type == MatchType.STRICT:
        return "strict"
    elif match_type == MatchType.FUZZY:
        return "fuzzy"
    else:
        return "no"


def prepare_match_strat_names(source_id: int):
    proc = sql_file("prepare-match-strat-names")
    db = get_database()

    db.run_sql(proc, {"source_id": source_id})

    # We now use the matched strat names for both this step and the
    # extract_strat_name_candidates step, so we use the same query file
    create_temp_names_table = "CREATE TABLE temp_names AS \n" + sql_file(
        "matched-strat-names"
    )

    db.run_sql(
        create_temp_names_table,
        {
            "source_id": source_id,
            "id_field": Identifier("map_id"),
            "match_field": Identifier("strat_name"),
            "match_table": Identifier("maps", "polygons"),
        },
    )

    for field in ["strat_name", "rank_name", "name_no_lith", "strat_name_id"]:
        db.run_sql("CREATE INDEX ON temp_names ({field})", {"field": Identifier(field)})


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
