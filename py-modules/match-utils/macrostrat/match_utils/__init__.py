from contextvars import ContextVar

from geopandas import GeoDataFrame
from pandas import isna, read_sql
from pydantic import BaseModel
from sqlalchemy.sql import text

from macrostrat.database import Database

from .models import MatchComparison, MatchResult, MatchType
from .strat_names import (
    clean_strat_name,
    clean_strat_name_text,
    create_ignore_list,
    format_name,
)
from .utils import stored_procedure

_column_unit_index = {}


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
    gdf = GeoDataFrame.from_postgis(
        text(sql), db.engine.connect(), geom_col="col_area", index_col="col_id"
    )
    return gdf


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

    types = get_match_types(types)

    units_df = read_sql(
        stored_procedure("column-strat-names"),
        conn,
        params=dict(
            col_id=col_id,
            use_concepts=MatchType.Concepts in types,
            use_synonyms=MatchType.Synonyms in types,
            use_adjacent_cols=MatchType.AdjacentCols in types,
            use_footprint_index=MatchType.FootprintIndex in types,
            use_column_units=MatchType.ColumnUnits in types,
        ),
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
    comparison: MatchComparison = MatchComparison.Included,
    types: list[MatchType] = None,
):
    """
    Get a unit that matches a given stratigraphic name within a given
    Macrostrat column.
    """
    rows = get_all_matched_units(
        conn, col_id, strat_names, comparison=comparison, types=types, n_results=1
    )
    if len(rows) == 0:
        return None

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
    comparison: MatchComparison = MatchComparison.Included,
    types: list[MatchType] = None,
    n_results: int | None = None,
    t_age: float | None = None,
    b_age: float | None = None,
):
    """
    Return all units and stratigraphic names that match the given col_id
    """

    units = get_column_units(conn, col_id, types=types)
    # Units matching age constraints only
    if b_age is not None:
        units = units.loc[units.t_age <= b_age]
    if t_age is not None:
        units = units.loc[units.b_age >= t_age]

    u1 = units[units.strat_name_clean.notnull()]

    matched_rows = []
    # The max number of results to return
    n_results = n_results or len(u1)

    # Perform matching in stages
    for ix, row in u1.iterrows():
        matches, _ = match_row(row, strat_names, comparison)
        if not matches:
            continue
        matched_rows.append(row)
        if len(matched_rows) >= n_results:
            return matched_rows
    return matched_rows


def match_row(row, strat_names, comparison) -> tuple[bool, MatchComparison | None]:
    # We don't support fuzzy matching yet
    if comparison == MatchComparison.Fuzzy:
        raise NotImplementedError("Fuzzy matching not implemented")

    name = row["strat_name_clean"]
    if name is None:
        return False, None
    # First try exact match, in all cases
    for strat_name in strat_names:
        if strat_name.name == name:
            return True, MatchComparison.Exact
    if comparison == MatchComparison.Exact:
        return False, None

    # Name is a subset of the strat name
    for strat_name in strat_names:
        # Try for a "like" match, which might catch verbatim strat names better
        if name in strat_name.name:
            return True, MatchComparison.Included

    if comparison == MatchComparison.Included:
        return False, None

    # "Bidirectional" matching: strat name can be either a subset or superset of the cleaned name
    for strat_name in strat_names:
        # Finally check that our cleaned strat name does not include the cleaned name as a subset
        if strat_name.name in name:
            return True, MatchComparison.Bidirectional

    return False, None


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
