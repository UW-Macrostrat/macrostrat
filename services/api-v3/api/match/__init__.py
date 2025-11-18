from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

from macrostrat.core.database import get_database
from macrostrat.match_utils import (
    MatchResult,
    MatchType,
    MatchComparison,
    ensure_single,
    get_columns_for_location,
    standardize_names,
    get_all_matched_units,
    get_match_types,
)

router = APIRouter(prefix="/match", tags=["match"])


class MatchQuery(BaseModel):
    match_text: str = Field(
        ..., description="Text containing a stratigraphic name to match."
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

    min_age: int = Field(0, description="Minimum age constraint in Ma.")
    max_age: int = Field(4600, description="Maximum age constraint in Ma.")

    # Enforce one of col_id or lat/lng
    def validate(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Lat and lng must both be provided.")
        if self.col_id is None and (self.lat is None or self.lng is None):
            raise ValueError("Either col_id or lat/lng must be provided.")


class MatchData(MatchQuery):
    matches: list[MatchResult]


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


class MatchOptions(BaseModel):
    basis: set[MatchType] = Field(
        set(get_match_types(None)), description="Types of matches to include."
    )
    comparison: MatchComparison = Field(
        MatchComparison.Included,
        description="Type of string comparison to perform.",
    )


@router.get("/strat-names", response_model=MatchAPIResponse)
def match_units(
    params: MatchQuery, opts: MatchOptions = MatchOptions()
) -> MatchAPIResponse:
    """
    Match stratigraphic names to Macrostrat units.
    """

    params.validate()

    db = get_database()

    col_id = params.col_id
    if col_id is None:
        col_id = ensure_single(get_columns_for_location(db, (params.lng, params.lat)))

    names = standardize_names(params.match_text)
    with db.engine.connect() as conn:
        results = get_all_matched_units(conn, col_id, names)

    match_data = MatchData(
        **params.model_dump(), matches=[MatchResult.from_row(r) for r in results]
    )

    return MatchAPIResponse(
        version="0.0.1",
        date_accessed=datetime.now().isoformat(),
        results=[match_data],
        **opts.model_dump(),
    )
