from contextvars import ContextVar

from geopandas import GeoDataFrame
from pandas import isna, read_sql
from pydantic import BaseModel
from sqlalchemy.sql import text

from macrostrat.database import Database

from .models import MatchResult, MatchType
from .strat_names import (
    clean_strat_name,
    clean_strat_name_text,
    create_ignore_list,
    format_name,
)
from .utils import stored_procedure

_column_unit_index = {}

MATCH_STRAT_NAMES_INFO = {
    "success": {
        "v": 2,
        "license": "CC-BY 4.0",
        "description": "Match stratigraphic names to Macrostrat columns and units. "
        "Accepts a stratigraphic name string, ID, or concept and returns "
        "matched Macrostrat units with associated metadata.",
        "options": {
            "_rules": [
                "Provide one of: strat_name, concept_name, strat_name_id, concept_id",
                "Provide one of: col_id, lat and lng",
            ],
            "parameters": {
                "strat_name": "string, stratigraphic name text to match (e.g. 'Navajo Sandstone'). "
                "Supports multiple names separated by semicolons.",
                "concept_name": "string, concept name text to match (e.g. 'Navajo'). "
                "Alternative to strat_name. Enables concept-based matching.",
                "strat_name_id": "integer, a Macrostrat stratigraphic name ID to match directly. "
                "Alternative to strat_name.",
                "concept_id": "integer, a Macrostrat concept ID to match directly. "
                "Alternative to concept_name. Can be combined with strat_name_id "
                "to filter by concept.",
                "lat": "number, latitude of the query location. Must be used with lng.",
                "lng": "number, longitude of the query location. Must be used with lat.",
                "col_id": "integer, a specific Macrostrat column ID. "
                "Can be used instead of lat/lng.",
                "priority": "string, controls how match results are prioritized when multiple possible matches are found. "
                "Allowed values: location | strat_name. Default: location. "
                "If priority=location, matches from the containing column are ranked before matches "
                "from adjacent columns, even if an adjacent-column match has a stronger stratigraphic "
                "name match. If priority=strat_name, results are ranked first by how closely the "
                "user's input stratigraphic name matches the stratigraphic name in the database, "
                "with exact name matches prioritized before broader concept, rank-down, rank-up, "
                "or synonym matches.",
                "project_id": "integer, limit search to a specific Macrostrat project. "
                "Useful when columns overlap across projects.",
                "interval": "string or integer, geologic time interval name or ID to constrain "
                "matches (e.g. 'Triassic'). Derives both b_age and t_age from the interval.",
                "b_interval": "string or integer, early/lower interval name or ID. "
                "Derives b_age from the bottom of this interval.",
                "t_interval": "string or integer, late/upper interval name or ID. "
                "Derives t_age from the top of this interval.",
                "b_age": "number, early/lower age constraint in millions of years (Ma). "
                "Must be greater than t_age.",
                "t_age": "number, late/upper age constraint in millions of years (Ma). "
                "Must be less than b_age.",
                "identifier": "string or integer, optional identifier to tag a query (e.g. a "
                "collection ID). Passed through to the response for correlation.",
                "all": "boolean, if true return all matches ordered by priority. "
                "If false (default), return only the highest priority match (priority=0.0).",
                "name_basis": "string, filter results to only those with this name_basis. "
                "One of: exact | concept | rank-down | rank-up | synonym. "
                "Applied as a final step after matching and prioritization. "
                "If all=true, returns every match with this name_basis; if all=false, "
                "returns the best (lowest-priority) match with this name_basis. "
                "Default: no filter (all bases returned).",
            },
            "output_formats": ["json"],
            "methods": {
                "GET": "Single query via URL parameters.",
                "POST": "Batch query — a JSON array of up to 100 query objects. Any field "
                "can be set per item, or shared across all items via a query parameter: "
                "query parameters act as defaults, so an item that omits a field inherits "
                "the query-parameter value and a field set on an item overrides it. This "
                "supports many names at one location, one name across many locations, and "
                "bulk matching by strat_name_id. Each item's optional 'identifier' is echoed "
                "back as 'id' on the corresponding result for correlation. Example: "
                "POST /dev/match/strat-names?lat=39.41922&lng=-111.95068&all=true with body "
                "[{\"identifier\": 932043, \"strat_name\": \"Navajo\"}, "
                "{\"identifier\": 74382, \"strat_name\": \"Navajo Sandstone\"}].",
            },
            "examples": [
                "/dev/match/strat-names?strat_name=Navajo Sandstone&lat=35.951&lng=-109.905",
                "/dev/match/strat-names?strat_name=Navajo Sandstone&lat=35.951&lng=-109.905&all=true",
                "/dev/match/strat-names?strat_name=Jelm Formation&lat=40.9&lng=-105.6&interval=Triassic",
                "/dev/match/strat-names?strat_name=Jelm Formation&lat=40.9&lng=-105.6&b_age=250.0&t_age=200.0",
                "/dev/match/strat-names?strat_name=Jelm Formation&lat=40.9&lng=-105.6&b_interval=Triassic&t_interval=Jurassic",
                "/dev/match/strat-names?strat_name=Navajo Sandstone&lat=35.951&lng=-109.905&all=true&name_basis=rank-up",
                "/dev/match/strat-names?strat_name=Kaza&lat=53.114&lng=-120.909&project_id=1",
                "/dev/match/strat-names?strat_name=Halgaito Member&lat=35.951&lng=-109.905&identifier=sample-001",
                "/dev/match/strat-names?strat_name_id=3361&lat=35.951&lng=-109.905",
                "/dev/match/strat-names?strat_name=Navajo Sandstone&lat=35.951&lng=-109.905&priority=location",
                "/dev/match/strat-names?strat_name=Navajo Sandstone&lat=35.951&lng=-109.905&priority=strat_name",
            ],
            "response_fields": {
                "results": "array, list of match result objects, one per query.",
                "results[].unit_matches": "array, matched units ordered by ascending priority.",
                "results[].messages": "array, any warnings or errors for this query.",
                "name_bases": "set of strings, the name_basis values present across all results.",
                "strat_name_id": "integer, Macrostrat stratigraphic name ID",
                "strat_name": "string, stratigraphic name",
                "strat_rank": "string, stratigraphic rank (e.g. Fm, Mbr, Gp)",
                "parent_id": "integer, parent stratigraphic name ID in the hierarchy",
                "concept_id": "integer, Macrostrat concept ID linked to this name",
                "concept_name": "string, concept name linked to this stratigraphic name",
                "unit_id": "integer, Macrostrat unit ID",
                "col_id": "integer, Macrostrat column ID",
                "project_id": "integer, Macrostrat project ID",
                "depth": "integer, hierarchy traversal depth (0=direct, negative=parent/rank-up, positive=child/rank-down)",
                "name_basis": "string, matching strategy that produced this result. "
                "One of: exact | concept | rank-up | rank-down | synonym",
                "spatial_basis": "string, spatial relationship of the match. "
                "One of: containing column | adjacent column",
                "t_age": "number, continuous time age model estimated top age, in Ma",
                "b_age": "number, continuous time age model estimated bottom age, in Ma",
                "priority": "number, match priority assigned after applying the selected priority ordering scheme. "
                "0.0 is the best match, and higher numbers indicate lower-priority matches. "
                "When priority=location, containing-column matches are prioritized before adjacent-column matches: "
                "exact/containing, concept/containing, rank-down/containing, rank-up/containing, "
                "synonym/containing, exact/adjacent, concept/adjacent, rank-down/adjacent, "
                "rank-up/adjacent, synonym/adjacent. "
                "When priority=strat_name, stronger stratigraphic name matches are prioritized first: "
                "exact/containing, exact/adjacent, concept/containing, rank-down/containing, "
                "concept/adjacent, rank-down/adjacent, rank-up/containing, rank-up/adjacent, "
                "synonym/containing, synonym/adjacent.",
            },
        },
    }
}


def get_match_types(types: list[MatchType] | None) -> list[MatchType]:
    if types is None:
        return [
            MatchType.ColumnUnits,
            MatchType.Concepts,
            MatchType.FootprintIndex,
            MatchType.AdjacentCols,
            MatchType.Synonyms,
        ]
    return types


def get_columns_data_frame(db: Database):
    """Get all Macrostrat columns as a GeoDataFrame"""
    sql = """
          SELECT col_id, ST_SetSRID(ca.col_area, 4326) as col_area
          FROM macrostrat.col_areas ca
                   JOIN macrostrat.cols c
                        ON c.id = ca.col_id
          WHERE c.status_code = 'active'
          """
    with db.engine.connect() as conn:
        return GeoDataFrame.from_postgis(
            text(sql), conn, geom_col="col_area", index_col="col_id"
        )


class ColumnInfo(BaseModel):
    col_id: int
    project_id: int
    status_code: str

    model_config = {
        "from_attributes": True,
    }


def get_columns_for_location(
    db, position, *, project_id=None, status_code="active"
) -> list[ColumnInfo]:
    """
    Get a list of column IDs for a given lat/lng position
    """

    base_select = """
    SELECT col_id, status_code, project_id FROM macrostrat.col_areas ca
    JOIN macrostrat.cols c ON c.id = ca.col_id
    """

    filters = ["ST_Contains(ca.col_area, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))"]
    params = dict(lng=position[0], lat=position[1])

    if status_code is not None:
        filters.append("c.status_code = :status_code")
        params["status_code"] = status_code

    if project_id is not None:
        filters.append("c.project_id = :project_id")
        params["project_id"] = project_id

    sql = base_select + " WHERE " + " AND ".join(filters)
    cols = db.run_query(sql, params).all()
    return [ColumnInfo.model_validate(row) for row in cols]


def get_adjacent_cols_from_containing(
    db, col_id, *, use_adjacent_cols=True, buffer=0.01
) -> list[int]:
    """
    Given the column returned by get_columns_for_location(), return the list of the adjacent columns.
    Adjacent columns query comes from the column-strat-names sql.
    """
    sql = """
    WITH RECURSIVE cols AS (
        SELECT col_id, ST_SetSRID(ca.col_area, 4326) AS col_area
        FROM macrostrat.col_areas ca
        JOIN macrostrat.cols c ON c.id = ca.col_id
        WHERE c.status_code = 'active'
    ),
    selected_col AS (
        SELECT * FROM cols WHERE col_id = :col_id
    ),
    adjacent_cols AS (
        SELECT cols.col_id, cols.col_id = sel.col_id AS selected
        FROM cols
        JOIN selected_col sel
            ON ST_Intersects(cols.col_area, ST_Buffer(sel.col_area, :buffer))
        WHERE :use_adjacent_cols OR cols.col_id = sel.col_id
    )
    --containing column first, then adjacent
    SELECT col_id FROM adjacent_cols
    ORDER BY selected DESC, col_id
    """
    params = dict(col_id=col_id, use_adjacent_cols=use_adjacent_cols, buffer=buffer)
    rows = db.run_query(sql, params).all()
    return [row.col_id for row in rows]


def ensure_single(col_ids, entity="column"):
    if len(col_ids) == 0:
        raise ValueError(f"No {entity}s found for location")
    if len(col_ids) > 1:
        raise ValueError(
            f"Multiple {entity}s found for location. This is not supported."
        )
    return col_ids[0]


column_unit_index = ContextVar("column_unit_index", default={})


def get_column_units(conn, col_id, types: list[MatchType] = None):
    """
    Get a unit that matches a given stratigraphic name
    """
    unit_index = column_unit_index.get()
    if col_id in unit_index:
        return unit_index[col_id]
    # TODO need to update the match types model to exact, concept, rank-up, rank-down
    types = get_match_types(types)

    params = dict(
        col_id=col_id,
        use_concepts=MatchType.Concepts in types,
        use_synonyms=MatchType.Synonyms in types,
        use_adjacent_cols=MatchType.AdjacentCols in types,
        use_footprint_index=MatchType.FootprintIndex in types,
        use_column_units=MatchType.ColumnUnits in types,
    )
    sql = stored_procedure("column-strat-names")
    units_df = read_sql(
        sql,
        conn,
        params=params,
        coerce_float=False,
    )
    # Insert column strat_name_clean after strat_name
    ix = units_df.columns.get_loc("strat_name")
    units_df.insert(
        ix + 1, "strat_name_clean", units_df["strat_name"].apply(clean_strat_name_text)
    )

    # Fix multiple project_id columns (not sure why this is happening)
    units_df = units_df.loc[:, ~units_df.columns.duplicated()]

    # Set the index to a shared cache
    unit_index = column_unit_index.get()
    unit_index[col_id] = units_df
    column_unit_index.set(unit_index)
    return units_df


def get_matched_unit(
    conn,
    col_id,
    strat_names,
    *,
    types: list[MatchType] = None,
):
    """
    Get a unit that matches a given stratigraphic name within a given
    Macrostrat column.
    """
    rows = get_all_matched_units(conn, col_id, strat_names, types=types, n_results=1)
    if len(rows) == 0:
        return None

    # TODO: the get_all_matched_units function now returns a tuple.
    # We might choose to fix this
    return rows[0]


def output_schema(schema):
    """Decorator to convert function output to a list of schema instances."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return [schema.from_row(row) for row in result]

        return wrapper

    return decorator


def get_all_matched_units(
    conn,
    col_id,
    strat_names,
    *,
    types: list[MatchType] = None,
    n_results: int | None = None,
    t_age: float | None = None,
    b_age: float | None = None,
) -> list[tuple]:
    """
    Return all units and stratigraphic names that match the given col_id.
    Returns list of (row, is_exact_name_match) tuples.
    """
    units = get_column_units(conn, col_id, types=types)
    if b_age is not None:
        units = units.loc[units.t_age <= b_age]
    if t_age is not None:
        units = units.loc[units.b_age >= t_age]

    u1 = units[units.strat_name_clean.notnull()]
    matched_rows = []
    n_results = n_results or len(u1)

    for ix, row in u1.iterrows():
        # Matches all units found from the col_id's to the provided strat_name
        matched, is_exact = match_row(row, strat_names)
        # true, true is exact match and true, false is concept/included match.
        if not matched:
            continue
        row["is_exact_name_match"] = is_exact
        matched_rows.append(row)
        if len(matched_rows) >= n_results:
            return matched_rows
    return matched_rows


def match_row(row, strat_names) -> tuple[bool, bool]:
    """
    Returns (matched, is_exact_name_match).
    Always uses 'included' logic — exact is tried first, then included.
    """
    name = row["strat_name_clean"]
    if name is None:
        return False, False

    # Try exact match first
    for strat_name in strat_names:
        if strat_name.name == name:
            return True, True

    # Fall back to included match
    # change to concept
    for strat_name in strat_names:
        if name in strat_name.name:
            return True, False

    return False, False


def standardize_names(source_text):
    res = []
    names = source_text.split(";")
    name_index = set()

    for name in names:
        out_name = clean_strat_name(name)

        for n1 in out_name:
            if n1.name in name_index:
                continue
            # Tracker for names
            name_index.add(n1.name)
            res.append(n1)

    return tuple(sorted(deduplicate_strat_names(res)))


def standardize_names_from_id(db, strat_name_id: int, concept_id: int | None):
    """Look up a strat name by ID and convert it to standardized names."""
    if concept_id is None:
        result = db.run_query(
            "SELECT strat_name FROM macrostrat.strat_names WHERE id = :id",
            {"id": strat_name_id},
        ).first()
        include_concept = False
    else:
        result = db.run_query(
            "SELECT strat_name FROM macrostrat.strat_names WHERE concept_id = :concept_id",
            {"concept_id": concept_id},
        ).first()
        include_concept = True
    if result is None:
        raise ValueError(
            f"No stratigraphic name found for strat_name_id={strat_name_id}"
        )
    return standardize_names(result.strat_name), include_concept


def format_names(strat_names, **kwargs):
    # Ignore nan values
    if isna(strat_names):
        return strat_names
    # if it's already a string, return it
    if isinstance(strat_names, str):
        return strat_names

    return ", ".join([format_name(i, **kwargs) for i in strat_names])


def deduplicate_strat_names(samples):
    return list(set(samples))
