import enum
from contextvars import ContextVar
from datetime import datetime
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, model_validator

from macrostrat.match_utils import (
    MATCH_STRAT_NAMES_INFO,
    MatchResult,
    create_ignore_list,
    get_all_matched_units,
    get_columns_for_location,
    standardize_names,
    standardize_names_from_id,
)
from macrostrat.match_utils.strat_names import get_ignore_list

from ..database import get_sync_database as get_database


class Interval(BaseModel):
    id: int
    interval_name: str
    age_bottom: float
    age_top: float


# Context variable to hold interval list
_intervals: ContextVar[list[Interval] | None] = ContextVar("intervals", default=None)


def setup_intervals(db):
    """Load intervals from the database and store them in the context variable."""
    # Get intervals from database
    val = _intervals.get()
    if val is not None:
        return  # Already initialized

    res = db.run_query(
        "SELECT id, interval_name, age_bottom, age_top FROM macrostrat.intervals"
    )
    interval_list = [Interval.model_validate(obj, from_attributes=True) for obj in res]
    _intervals.set(interval_list)


def setup_matcher():
    """Setup function to initialize matcher resources."""
    db = get_database()
    try:
        ignore = get_ignore_list()
        return
    except ValueError:
        lith_names = (
            db.run_query("SELECT lith name FROM macrostrat.liths").scalars().all()
        )
        create_ignore_list(lith_names)

    setup_intervals(db)


router = APIRouter(tags=["match"])


class AbsoluteAgeConstraint(BaseModel):
    b_age: float = Field(None, description="Early/lower age constraint in Ma")
    t_age: float = Field(None, description="Late/upper age constraint in Ma")


class MatchQueryFields(BaseModel):
    """All fields of a single match query, with no cross-field validation.

    Used directly as the element type of the batch POST body, where every field
    is optional because omitted fields inherit shared defaults from the query
    string. The validated form is MatchQuery, which adds the location and
    strat_name/strat_name_id checks once defaults have been merged in.
    """

    strat_name: str | None = Field(
        None,
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
    concept_name: str | None = Field(
        None,
        description="Text containing a concept name to match.",
        examples=[
            "Navajo",
            "Dakota",
            "Morrison",
            "Kayenta",
        ],
    )
    strat_name_id: int | None = Field(
        None, description="A Macrostrat stratigraphic name ID to match directly."
    )
    concept_id: int | None = Field(
        None, description="A Macrostrat concept ID to match directly."
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
    b_interval: int | str | None = Field(
        None, description="Early/lower interval name or ID"
    )
    t_interval: int | str | None = Field(
        None, description="Late/upper interval name or ID"
    )
    interval: int | str | None = Field(
        None, description="Interval name or ID to constrain matches"
    )
    b_age: float | None = Field(None, description="Early/lower age constraint in Ma")
    t_age: float | None = Field(None, description="Late/upper age constraint in Ma")
    priority: Literal["strat_name", "location"] = Field(
        "location",
        description=(
            "Controls how match results are prioritized when multiple possible matches are found. "
            "If priority='location', matches from the containing column are ranked before matches "
            "from adjacent columns, even if an adjacent-column match has a stronger stratigraphic "
            "name match. This is the default behavior. "
            "If priority='strat_name', results are ranked first by how closely the user's input "
            "stratigraphic name matches the stratigraphic name in the database, with exact name "
            "matches prioritized before broader concept, rank-down, rank-up, or synonym matches."
        ),
    )

    def get_age_range(self) -> AbsoluteAgeConstraint:
        """Get the best age constraint from the provided age or interval names/IDs."""

        # Start with unconstrained ages
        b_age = float("inf")
        t_age = -float("inf")

        # Apply interval-based age constraints in order of specificity, complaining if conflicting
        if self.interval is not None:
            intv = get_interval(self.interval)
            b_age = intv.age_bottom
            t_age = intv.age_top

        if self.b_interval is not None:
            intv = get_interval(self.b_interval)
            b_age = min(b_age, intv.age_bottom)
        if self.t_interval is not None:
            intv = get_interval(self.t_interval)
            t_age = max(t_age, intv.age_top)
        if self.b_age is not None:
            b_age = min(b_age, self.b_age)
        if self.t_age is not None:
            t_age = max(t_age, self.t_age)
        return AbsoluteAgeConstraint(b_age=b_age, t_age=t_age)


class MatchQuery(MatchQueryFields):
    """A single, fully-validated match query.

    Adds the cross-field rules that only make sense once all values are present
    (after any shared defaults have been merged in).
    """

    @model_validator(mode="after")
    def validate_position_info(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Lat and lng must both be provided.")
        if self.col_id is None and (self.lat is None or self.lng is None):
            raise ValueError("Either col_id or lat/lng must be provided.")
        return self

    @model_validator(mode="after")
    def validate_match_input(self):
        """Ensure that exactly one of strat_name or strat_name_id is provided."""
        if (
            self.strat_name is None
            and self.strat_name_id is None
            and self.concept_id is None
            and self.concept_name is None
        ):
            raise ValueError(
                "Either strat_name/concept_name or strat_name_id/concept_id must be provided."
            )
        if self.strat_name is not None and self.strat_name_id is not None:
            raise ValueError(
                "Only one of strat_name or strat_name_id can be provided, not both."
            )
        return self


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


class MatchData(BaseModel):
    id: str | int | None = Field(
        None,
        description="The identifier supplied with the input query, echoed back so "
        "batch results can be correlated to their input.",
    )
    unit_matches: list[MatchResult]
    messages: list[MatchMessage]


class MatchAPIResponse(BaseModel):
    version: str
    date_accessed: str
    results: list[MatchData]
    name_bases: set[str] = Field(
        ..., description="The match basis values present in the result set."
    )
    messages: set[MatchMessage] | None = None


NameBasis = Literal["exact", "concept", "rank-down", "rank-up", "synonym"]
SpatialBasis = Literal["containing column", "adjacent column"]


class MatchOptions(BaseModel):
    name_basis: Optional[NameBasis] = Field(
        None,
        description="If provided, filter results to only those whose name_basis "
        "equals this value. One of: exact, concept, rank-down, rank-up, synonym. "
        "Applied as a final step after matching and prioritization.",
    )
    all: bool = Field(
        False,
        description="Return all matches. If false, only return the best priority match.",
    )


class MatchSingleQueryParams(MatchQuery, MatchOptions):
    pass


class MatchDefaults(MatchQueryFields, MatchOptions):
    """Shared defaults for a batch POST, supplied as query parameters.

    Any field omitted from a body item inherits the value provided here, and a
    field set on a body item overrides it. This keeps a single request shape (a
    list of MatchQuery objects) while letting callers factor out whatever is
    common — a location, a strat_name, an age range — into the query string.
    """


class MatchPriorityOrder(BaseModel):
    """
    A single priority-ordering rule used to rank match results.
    Each rule combines two pieces of information:
    - name_basis: how the user's input stratigraphic name matched the database record
      such as exact, concept, rank-down, rank-up, or synonym.
    - spatial_basis: how the matched unit relates to the input location or column,
      such as containing column or adjacent column.
    The API supports different priority schemes. With priority='location', spatial
    relationship is favored first, so containing-column matches are ranked before
    adjacent-column matches. With priority='strat_name', the strength of the
    stratigraphic name match is favored first.
    """

    name_basis: NameBasis = Field(
        ...,
        description=(
            "How the user's input stratigraphic name matched the database record. "
            "For example, 'exact' means the input name directly matched the database "
        ),
    )
    spatial_basis: SpatialBasis = Field(
        ...,
        description=(
            "Spatial relationship between the matched unit and the column location. "
            "'containing column' means the match comes from the column containing the user's input "
            "'adjacent column' means the match comes from a neighboring column. "
        ),
    )

    def priority_matches(self, result: MatchResult) -> bool:
        return (
            result.name_basis == self.name_basis
            and result.spatial_basis == self.spatial_basis
        )


PRIORITY_ORDER = [
    MatchPriorityOrder(name_basis="exact", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="exact", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="concept", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="rank-down", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="concept", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="rank-down", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="rank-up", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="rank-up", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="synonym", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="synonym", spatial_basis="adjacent column"),
]

PRIORITY_ORDER_LOCATION = [
    MatchPriorityOrder(name_basis="exact", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="concept", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="rank-down", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="rank-up", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="synonym", spatial_basis="containing column"),
    MatchPriorityOrder(name_basis="exact", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="concept", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="rank-down", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="rank-up", spatial_basis="adjacent column"),
    MatchPriorityOrder(name_basis="synonym", spatial_basis="adjacent column"),
]


def assign_priorities(
    results: list[MatchResult], priority: str = "location"
) -> list[MatchResult]:
    """Assign consecutive priorities based on name_basis/spatial_basis combinations present."""

    order = PRIORITY_ORDER_LOCATION if priority == "location" else PRIORITY_ORDER
    present: list[MatchPriorityOrder] = []

    for priority_rule in order:
        if any(priority_rule.priority_matches(r) for r in results):
            if priority_rule not in present:
                present.append(priority_rule)

    updated = []
    for result in results:
        result_priority = float(len(present))
        for idx, priority_rule in enumerate(present):
            if priority_rule.priority_matches(result):
                result_priority = float(idx)
                break
        updated.append(result.model_copy(update={"priority": result_priority}))

    return sorted(updated, key=lambda r: r.priority)


def get_interval(interval: int | str) -> Optional[Interval]:
    """Retrieve interval information by ID or name."""
    interval_list = _intervals.get()
    if interval_list is None:
        raise ValueError("Interval list not initialized.")

    for intv in interval_list:
        if isinstance(interval, int) and intv.id == interval:
            return intv
        elif isinstance(interval, str) and intv.interval_name == interval:
            return intv
    return None


@router.get("/")
def match_info():
    """Return self-documenting info for the match API."""
    return MATCH_STRAT_NAMES_INFO


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

    db = get_database()
    try:
        setup_matcher()

        results = []
        match_data = build_match_data(db, params)
        if match_data is not None:
            results.append(match_data)
            print("Match data results", results)
        return generate_response(results, opts)
    finally:
        # Release this thread's scoped session so its connection returns to the
        # pool. Without this, queries run via db.run_query leave an open
        # transaction (run_query never advances the underlying generator to its
        # commit), leaking a connection per worker thread until the pool is
        # exhausted.
        db.session.remove()


@router.post("/strat-names")
def match_units_multi(
    body: list[MatchQueryFields],
    defaults: Annotated[MatchDefaults, Query()],
) -> MatchAPIResponse:
    """
    Match a batch of stratigraphic name queries in a single request.

    The body is a JSON array of query objects. Any field can be set per item, or
    shared across all items via a query parameter: query parameters act as
    **defaults**, so an item that omits a field inherits the query-parameter
    value, and a field set on an item overrides it. This supports many names at
    one location, one name across many locations, and bulk matching by
    strat_name_id — all with one request and one response shape.

    :return: MatchAPIResponse
    """
    # Response-shaping options are request-wide (query string only).
    opts = MatchOptions(all=defaults.all, name_basis=defaults.name_basis)
    # Per-item defaults: only the query params the caller actually set.
    default_fields = defaults.model_dump(
        exclude_unset=True, exclude={"all", "name_basis"}
    )

    if len(body) > 100:
        raise HTTPException(
            status_code=422, detail="Maximum of 100 queries allowed per request."
        )

    # Merge defaults under each item (item wins) and validate the result.
    queries: list[MatchQuery] = []
    for index, item in enumerate(body):
        merged = {**default_fields, **item.model_dump(exclude_unset=True)}
        try:
            queries.append(MatchQuery(**merged))
        except ValidationError as err:
            raise HTTPException(
                status_code=422,
                detail=[{**e, "index": index} for e in err.errors()],
            )

    db = get_database()
    try:
        setup_matcher()

        all_results: list[MatchData] = []
        for params in queries:
            match_data = build_match_data(db, params)
            if match_data is not None:
                all_results.append(match_data)

        return generate_response(all_results, opts)
    finally:
        db.session.remove()


def generate_response(
    results: list[MatchData], opts: MatchOptions, messages: list[MatchMessage] = None
) -> MatchAPIResponse:
    # Filter by name_basis after matching/prioritization, keeping only matches
    # whose name_basis equals the requested value.
    if opts.name_basis is not None:
        results = [
            MatchData(
                id=result.id,
                unit_matches=[
                    m for m in result.unit_matches if m.name_basis == opts.name_basis
                ],
                messages=result.messages,
            )
            for result in results
        ]

    # When all=False, keep only the best (lowest-priority) match that remain.
    # With no name_basis filter the best priority is 0.0, preserving prior behavior.
    if not opts.all:
        reduced: list[MatchData] = []
        for result in results:
            if result.unit_matches:
                best = min(m.priority for m in result.unit_matches)
                kept = [m for m in result.unit_matches if m.priority == best]
            else:
                kept = []
            reduced.append(
                MatchData(id=result.id, unit_matches=kept, messages=result.messages)
            )
        results = reduced
    _messages: set[MatchMessage] = set()

    for result in results:
        if result.messages is None:
            continue
        for msg in result.messages:
            _messages.add(msg)

    if len(results) == 0:
        _messages.add(MatchMessage(message="No matches found"))

    if messages is not None:
        for msg in messages:
            _messages.add(msg)

    name_basis_values = {
        match.name_basis for result in results for match in result.unit_matches
    }

    return MatchAPIResponse(
        version="0.0.1",
        date_accessed=datetime.now().isoformat(),
        results=results,
        messages=messages,
        name_bases=name_basis_values,
    )


def _all_params_match(vals: dict, params: MatchQuery) -> bool:
    """Check whether all user-supplied params match the row values."""
    if (
        params.strat_name_id is not None
        and vals.get("strat_name_id") != params.strat_name_id
    ):
        return False
    if params.concept_id is not None and vals.get("concept_id") != params.concept_id:
        return False
    if params.b_age is not None and (
        vals.get("b_age") is None or vals["b_age"] < params.b_age
    ):
        return False
    if params.t_age is not None and (
        vals.get("t_age") is None or vals["t_age"] > params.t_age
    ):
        return False
    return True


def compute_name_basis(
    vals: dict, is_exact_name_match: bool, params: MatchQuery
) -> str:
    """Compute the name_basis value for a result row."""
    sql_basis = vals.get("basis", "")

    if sql_basis == "concept":
        return "concept"
    if sql_basis == "synonym":
        return "synonym"

    depth = vals.get("depth") or 0
    if depth == 0 and is_exact_name_match and _all_params_match(vals, params):
        return "exact"
    if depth > 0:
        return "rank-down"
    if depth < 0:
        return "rank-up"

    return "concept"


def build_match_data(db, params):
    """Build MatchData for a single MatchQuery."""

    age_constraint = params.get_age_range()
    print("age_constraint", age_constraint)
    res = params.model_dump()
    # Add resolved numeric age constraints to context if provided
    if age_constraint.t_age >= 0:
        res["t_age"] = age_constraint.t_age
    if age_constraint.b_age < 4600:
        res["b_age"] = age_constraint.b_age
    print("params dumped into a model dict", res)

    if params.strat_name is not None and params.concept_name is not None:
        # Return an error result
        return MatchData(
            id=params.identifier,
            unit_matches=[],
            messages=[
                MatchMessage(
                    message="Please input either a valid strat_name OR concept_name. Both are not accepted. ",
                    type=MatchMessageType.Error,
                )
            ],
        )

    # Validate age constraint
    if age_constraint.b_age < age_constraint.t_age:
        # Return an error result
        return MatchData(
            id=params.identifier,
            unit_matches=[],
            messages=[
                MatchMessage(
                    message="Inconsistent age constraints: b_age < t_age",
                    type=MatchMessageType.Error,
                )
            ],
        )

    col_id = params.col_id
    if col_id is None:
        cols = get_columns_for_location(db, (params.lng, params.lat))
        print("validate cols against pydantic model", cols)
        col_ids = [col.col_id for col in cols]
    else:
        col_ids = [col_id]

    results: list[MatchResult] = []
    messages: list[MatchMessage] = []
    print("here are the found col_ids", col_ids)
    for col_id in col_ids:
        if params.strat_name is not None:
            names = standardize_names(params.strat_name)
            print("standardized strat_name from user", names)
            include_concept = False
        elif params.concept_name is not None:
            names = standardize_names(params.concept_name)
            include_concept = True
        else:
            names, include_concept = standardize_names_from_id(
                db, params.strat_name_id, params.concept_id
            )
            print("standardized strat_name from user's strat_name_id parameter", names)

        with db.engine.connect() as conn:
            rows = get_all_matched_units(
                conn,
                col_id,
                names,
                t_age=age_constraint.t_age,
                b_age=age_constraint.b_age,
            )
        raw_name = (params.strat_name or params.concept_name or "").strip().lower()
        for row, is_exact in rows:
            vals = dict(row)
            db_name = (vals.get("strat_name") or "").strip().lower()
            is_exact = False if raw_name != db_name else is_exact
            print("raw name", raw_name, "db_name", db_name, "is_exact", is_exact)
            from pandas import isna

            for key, val in vals.items():
                if isna(val):
                    vals[key] = None
            if not include_concept and vals["basis"] == "concept":
                continue
            if vals["basis"] == "synonym":
                continue
            vals["name_basis"] = compute_name_basis(vals, is_exact, params)
            vals.pop("basis", None)
            results.append(MatchResult(**vals))

        print("results!", results)
    # TODO match based on lexicon footprints only if columns are not found.
    # organize in order to priorize
    if len(col_ids) > 1:
        messages.append(
            MatchMessage(
                message="Multiple columns",
                details="Results aggregated from multiple columns. Consider specifying a single col_id or project_id for more precise results.",
                type=MatchMessageType.Warning,
            )
        )
    results = assign_priorities(results, params.priority)
    return MatchData(id=params.identifier, unit_matches=results, messages=messages)
