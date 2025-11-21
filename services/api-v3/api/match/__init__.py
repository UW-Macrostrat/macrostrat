import enum
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from macrostrat.core.database import get_database
from macrostrat.match_utils import (
    MatchResult,
    MatchType,
    MatchComparison,
    get_columns_for_location,
    standardize_names,
    get_all_matched_units,
    get_match_types,
)

router = APIRouter(prefix="/match", tags=["match"])


class MatchQuery(BaseModel):
    match_text: str = Field(
        ...,
        description="Text containing a stratigraphic name to match.",
        examples=[
            "Navajo Sandstone",
            "Halgaito Member",
            "Coconino",
            "Dakota Formation",
            "Matchless Amphibolite",
            "broke neck pluton; Escapement Bay Fm",
            "Morrison Fm",
            "Kayenta Formation; Davis Branch Mbr; Wingate Sandstone",
        ],
    )
    identifier: str | int | None = Field(
        None, description="An optional identifier to associate with this query."
    )
    lat: float | None = None
    lng: float | None = None
    col_id: int | None = Field(
        None, description="Search within a specific Macrostrat column"
    )
    project_id: int | None = Field(
        None, description="Search within a specific Macrostrat project"
    )

    b_age: int | None = Field(None, description="Early/lower age constraint in Ma")
    t_age: int| None= Field(None, description="Late/upper age constraint in Ma")

    b_interval: int | str | None = Field(
        None, description="Early/lower interval name or ID"
    )
    t_interval: int | str | None = Field(
        None, description="Late/upper interval name or ID"
    )
    interval: int | str | None = Field(
        None, description="Interval name or ID to constrain matches"
    )

    # Enforce one of col_id or lat/lng
    def validate(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Lat and lng must both be provided.")
        if self.col_id is None and (self.lat is None or self.lng is None):
            raise ValueError("Either col_id or lat/lng must be provided.")


class MatchMessageType(enum.Enum):
    Info = "info"
    Warning = "warning"
    Error = "error"

    def __hash__(self):
        return hash(self.value)


class MatchMessage(BaseModel):
    message: str
    details: Optional[str] = None
    type: MatchMessageType = MatchMessageType.Info

    def __eq__(self, other):
        if not isinstance(other, MatchMessage):
            return NotImplemented

        return (
            self.type == other.type
            and self.message == other.message
            and self.details == other.details
        )

    def __hash__(self):
        return hash((self.type, self.message, self.details))


class MatchData(MatchQuery):
    matches: list[MatchResult]
    messages: list[MatchMessage]


class MatchAPIResponse(BaseModel):
    version: str
    date_accessed: str
    results: list[MatchData]
    basis: set[MatchType] = Field(
        ..., description="The types of matches that were included in the result set."
    )
    comparison: MatchComparison = Field(
        ..., description="The type of string comparison that was performed."
    )
    messages: set[MatchMessage] | None = None


class MatchOptions(BaseModel):
    basis: set[MatchType] = Field(
        set(get_match_types(None)), description="Types of matches to include."
    )
    comparison: MatchComparison = Field(
        MatchComparison.Included,
        description="Type of string comparison to perform.",
    )


class MatchSingleQueryParams(MatchQuery, MatchOptions):
    pass


@router.get("/strat-names")
def match_units(
    query: Annotated[MatchSingleQueryParams, Query()],
) -> MatchAPIResponse:
    """
    Match stratigraphic name text to the Macrostrat lexicon and columns.
    """
    # Reconstruct separated mixins
    params = MatchQuery(**query.model_dump())
    opts = MatchOptions(**query.model_dump())
    params.validate()

    db = get_database()

    results = []
    match_data = build_match_data(db, params)
    if match_data is not None:
        results.append(match_data)

    return generate_response(results, opts)


@router.post("/strat-names")
def match_units_multi(
    body: list[MatchQuery],
    query: Annotated[MatchOptions, Query()],
):
    """
    Match multiple stratigraphic name queries in a single request.
    :return: MatchAPIResponse
    """
    opts = MatchOptions(**query.model_dump())

    db = get_database()

    all_results: list[MatchData] = []

    if len(body) > 100:
        raise ValueError("Maximum of 100 queries allowed per request.")

    for params in body:
        params.validate()

    for params in body:
        match_data = build_match_data(db, params)
        if match_data is not None:
            all_results.append(match_data)

    return generate_response(all_results, opts)


def generate_response(results: list[MatchData], opts: MatchOptions) -> MatchAPIResponse:
    # Aggregate warnings across all results
    messages: set[MatchMessage] = set()
    for result in results:
        if result.messages is None:
            continue
        for msg in result.messages:
            messages.add(msg)

    # Could also raise an error/return a 404
    if len(results) == 0:
        messages.add(MatchMessage(message="No matches found"))

    return MatchAPIResponse(
        version="0.0.1",
        date_accessed=datetime.now().isoformat(),
        results=results,
        messages=messages,
        **opts.model_dump(),
    )


def build_match_data(db, params):
    col_id = params.col_id
    if col_id is None:
        cols = get_columns_for_location(db, (params.lng, params.lat))
        col_ids = [col.col_id for col in cols]
    else:
        col_ids = [col_id]

    results: list[MatchResult] = []
    messages: list[MatchMessage] = []
    for col_id in col_ids:
        names = standardize_names(params.match_text)
        with db.engine.connect() as conn:
            rows = get_all_matched_units(conn, col_id, names)
        results += [MatchResult.from_row(r) for r in rows]

    if len(results) == 0:
        return None

    # TODO match based on lexicon footprints only if columns are not found.

    if len(col_ids) > 1:
        messages.append(
            MatchMessage(
                message="Multiple columns",
                details="Results aggregated from multiple columns. Consider specifying a single col_id or project_id for more precise results.",
                type=MatchMessageType.Warning,
            )
        )

    return MatchData(**params.model_dump(), matches=results, messages=messages)
