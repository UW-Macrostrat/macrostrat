from dataclasses import dataclass, field
from enum import Enum

import polars as pl

from macrostrat.utils import get_logger

from .. import notices
from ..boundary_status import BoundaryStatus
from ..boundary_type import BoundaryType
from ..environs import Environ, EnvironsProcessor
from ..intervals import (
    Interval,
    RelativeAge,
    get_interval_by_id,
    get_interval_from_text,
    get_intervals,
)
from ..lithologies import LithAbundance, Lithology, LithsProcessor


@dataclass
class Unit:
    id: int = -1
    col_id: int = -1
    #: Database `sections.id`, assigned by `columns.sections.reconcile_sections` once the
    #: section exists. Membership itself is `Section.units`: a unit carries no section
    #: label of its own, and does not know its section until the section has an id.
    section_id: int = -1
    b_pos: float | None = None
    t_pos: float | None = None
    lithology: set[Lithology] = field(default_factory=set)
    environment: set[Environ] = field(default_factory=set)
    description: str | None = None
    #: Free-text remarks, kept apart from `description` because `unit_notes` composes the
    #: two into one note rather than storing either verbatim.
    comments: str | None = None
    name: str | None = None
    color: str | None = None
    #: The kind of surface at this unit's base, in the vocabulary of
    #: `unit_boundaries.boundary_type`; `None` where the source says nothing. A
    #: non-conformable base is what opens a new section in `columns.sections.split_at_gaps`,
    #: and inside a section it is warned about, since a section is meant to be conformable.
    b_surface_type: BoundaryType | None = None
    #: The identifier this unit carries in the dataset it came from, written to
    #: `macrostrat.units.orig_id` and preferred over the positional natural key when
    #: reconciling — see `units.writer.unit_identity`. `None` for workbook units, which
    #: have no source identifier and fall back to position.
    #:
    #: Unique within whatever scope the source declares — the section when the unit's
    #: `Section` carries its own `orig_id`, the column otherwise. Nothing to compose by
    #: hand.
    orig_id: str | None = None

    #: The spreadsheet row this unit came from, for notices. `None` off-workbook.
    row: int | None = None
    #: `macrostrat.units.outcrop`: `covered` for a unit present but unexposed, otherwise
    #: `subsurface` on a depth axis and `surface` elsewhere.
    outcrop: str = "surface"

    # Relative age positioning
    b_age: RelativeAge | None = None
    t_age: RelativeAge | None = None
    #: Where `b_age` / `t_age` came from, carried through to the `boundary_status`
    #: of the surfaces they constrain. `RELATIVE` — the source named an interval
    #: and a position within it — is the workbook case and so the default. A
    #: dataset with no chronostratigraphic anchors, whose ages are interpolated
    #: through thickness, sets `IMPOSED` on every unit instead.
    age_status: BoundaryStatus = BoundaryStatus.RELATIVE


log = get_logger(__name__)


def rename_aliases(df, aliases):
    """Rename or alias columns in a data frame"""
    warnings = set()
    for old_name, new_name in aliases.items():
        if old_name in df.columns:
            if new_name not in df.columns:
                df = df.rename({old_name: new_name})
            else:
                warnings.add(
                    f"Both '{old_name}' and '{new_name}' are present in the data frame."
                )
    return df, warnings


class PositionAxisType(str, Enum):
    HEIGHT = "height"
    DEPTH = "depth"
    ORDINAL = "ordinal"

    @classmethod
    def from_axis_type(cls, axis_type: str | None) -> "PositionAxisType":
        """The workbook's `axis_type`: `age` positions are an ordination of surfaces."""
        if axis_type == "age":
            return cls.ORDINAL
        if axis_type == "depth":
            return cls.DEPTH
        return cls.HEIGHT


#: The original spreadsheet row of each unit row, carried through sorting and grouping.
ROW_COLUMN = "_row"

#: Descriptive fields that `fill_values` carries along the axis (`name` is `unit_name`).
FILLED_FIELDS = (
    "lithology",
    "minor_lith",
    "environment",
    "grainsize",
    "color",
    "strat_name",
    "name",
    "facies",
)

#: In a filled field, the unit has no value, and a filled run ends.
NO_VALUE = "none"

#: Row markers, written as the unit name or lithology: a covered unit, or missing rock.
COVERED = "covered"
GAP = "gap"
MARKER_FIELDS = ("name", "lithology")

#: The default proportion of a blank `b_prop` / `t_prop`: an interval's oldest or youngest end.
DEFAULT_PROPORTION = {"b": 0, "t": 1}


def axis_bounds(position: PositionAxisType) -> tuple[str, str]:
    """`(leading, trailing)`: the bound each row's unit begins and ends at along the axis.

    A row is a surface and the unit after it, so on a depth axis it is the unit's top.
    """
    if position == PositionAxisType.DEPTH:
        return "t", "b"
    return "b", "t"


def prepare_section_units(
    db,
    df,
    *,
    position: PositionAxisType = PositionAxisType.HEIGHT,
    fill_values: bool = False,
    vocab=None,
) -> list[Unit]:
    """The rows of one section as `Unit`s.

    `vocab` is the run's `Vocabulary` (lithology and environment processors); one is
    built here when a caller has none, at the cost of a lookup fetch.
    """
    if vocab is None:
        from ..vocabulary import Vocabulary

        vocab = Vocabulary(db)

    lead, trail = axis_bounds(position)
    df = _with_position(df, lead + "_pos")
    for col in ("b_pos", "t_pos", "b_int", "t_int", "b_prop", "t_prop"):
        if col not in df.columns:
            df = df.with_columns(pl.lit(None).alias(col))
    # Ascending positions run along the axis on every axis type
    df = df.sort(pl.coalesce(lead + "_pos", trail + "_pos"), nulls_last=True)

    rows = df.to_dicts()
    _infer_bounds(rows, position)
    units, bounding, gaps = [], [], []
    for row in rows:
        marker = _marker(row)
        if marker == GAP:
            gaps.append(row)
        elif row["b_pos"] is None or row["t_pos"] is None:
            bounding.append(row)
        else:
            if marker == COVERED:
                row["covered"] = True
            units.append(row)
    _carry_ages(units, bounding + gaps, lead, trail)
    for row in bounding:
        _report_unplaced(row)

    _clean_filled_fields(
        units, fill=fill_values and position != PositionAxisType.ORDINAL
    )

    res = []
    for row in units:
        with notices.notice_context(row=row.get(ROW_COLUMN), unit=row.get("name")):
            res.append(_unit_from_row(db, row, vocab, position))
    return res


def _with_position(df, lead_pos: str):
    """Fold `position` into the bound it names on this axis."""
    if "position" not in df.columns:
        return df
    pos = pl.col("position").cast(pl.Float64, strict=False)
    if lead_pos not in df.columns:
        return df.with_columns(pos.alias(lead_pos)).drop("position")
    explicit = pl.col(lead_pos).cast(pl.Float64, strict=False)
    clashes = df.filter(explicit.is_not_null() & pos.is_not_null() & (explicit != pos))
    for row in clashes.iter_rows(named=True):
        notices.warning(
            "position-conflict",
            f"`position` {row['position']} and `{lead_pos}` {row[lead_pos]} disagree; "
            f"using `{lead_pos}`",
            row=row.get(ROW_COLUMN),
            column=lead_pos,
        )
    return df.with_columns(pl.coalesce(explicit, pos).alias(lead_pos)).drop("position")


def _infer_bounds(rows: list[dict], position: PositionAxisType) -> None:
    """Fill each row's missing bound from the next or previous surface along the axis."""
    lead, trail = (b + "_pos" for b in axis_bounds(position))
    if position == PositionAxisType.ORDINAL:
        # Slots: a unit at n rests on surface n and is capped by n + 1
        for row in rows:
            if row[trail] is None and row[lead] is not None:
                row[trail] = row[lead] + 1
            elif row[lead] is None and row[trail] is not None:
                row[lead] = row[trail] - 1
        return
    starts = sorted({r[lead] for r in rows if r[lead] is not None})
    ends = sorted({r[trail] for r in rows if r[trail] is not None})
    following = dict(zip(starts, starts[1:]))
    preceding = dict(zip(ends[1:], ends))
    for row in rows:
        start, end = row[lead], row[trail]
        if end is None and start is not None:
            row[trail] = following.get(start)
        elif start is None and end is not None:
            row[lead] = preceding.get(end)


def _age(row: dict, bound: str) -> tuple | None:
    """`(interval, proportion)` for one bound, with a blank proportion made explicit."""
    interval = row.get(bound + "_int")
    if _blank(interval):
        return None
    proportion = row.get(bound + "_prop")
    if _blank(proportion):
        proportion = DEFAULT_PROPORTION[bound]
    return interval, proportion


def _set_age(row: dict, bound: str, age: tuple) -> None:
    row[bound + "_int"], row[bound + "_prop"] = age


def _carry_ages(units: list[dict], bounding: list[dict], lead: str, trail: str) -> None:
    """Give each unit the age of a surface it shares, where it has none of its own.

    A unit's trailing surface is the next unit's leading one, so its age comes from
    there. A bounding row is only a surface, so either of its ages dates it.
    """
    starts: dict = {}
    for row in units:
        age = _age(row, lead)
        if age is not None:
            starts.setdefault(row[lead + "_pos"], age)
    marks: dict = {}
    for row in bounding:
        surface = _coalesce(row[lead + "_pos"], row[trail + "_pos"])
        age = _age(row, lead) or _age(row, trail)
        if surface is not None and age is not None:
            marks.setdefault(surface, age)
    for row in units:
        if _age(row, trail) is None:
            age = starts.get(row[trail + "_pos"]) or marks.get(row[trail + "_pos"])
            if age is not None:
                _set_age(row, trail, age)
        if _age(row, lead) is None and row[lead + "_pos"] in marks:
            _set_age(row, lead, marks[row[lead + "_pos"]])


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _report_unplaced(row: dict) -> None:
    """A bounding row is expected; a row with nothing to place it by is not."""
    name = row.get("name") or ""
    if row["b_pos"] is None and row["t_pos"] is None:
        notices.warning(
            "unit-missing-position",
            f"Unit {name!r} has no position and was left out",
            row=row.get(ROW_COLUMN),
            unit=row.get("name"),
            column="b_pos",
        )
        return
    described = [f for f in (*FILLED_FIELDS, "description") if not _blank(row.get(f))]
    if described:
        notices.warning(
            "closing-row-values-ignored",
            "This row only closes the unit next to it; its values are ignored: "
            + ", ".join(f"`{f}`" for f in described),
            row=row.get(ROW_COLUMN),
            unit=row.get("name"),
            column=described[0],
        )


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_no_value(value) -> bool:
    return isinstance(value, str) and value.strip().lower() == NO_VALUE


def _is_marker(value) -> bool:
    return isinstance(value, str) and value.strip().lower() in (COVERED, GAP)


def _marker(row: dict) -> str | None:
    for field_name in MARKER_FIELDS:
        if _is_marker(row.get(field_name)):
            return row[field_name].strip().lower()
    return None


def _clean_filled_fields(rows: list[dict], *, fill: bool) -> None:
    """Blank cells take the previous row's value along the axis; `none` ends a run."""
    last: dict = {}
    for row in rows:
        for field_name in FILLED_FIELDS:
            if field_name not in row:
                continue
            value = row[field_name]
            if field_name in MARKER_FIELDS and _is_marker(value):
                # A marker describes this row only, so the run continues past it
                value = None
            elif _is_no_value(value):
                value = None
                last[field_name] = None
            elif _blank(value):
                value = last.get(field_name) if fill else None
            else:
                last[field_name] = value
            row[field_name] = value


def _unit_from_row(db, row: dict, vocab, position=PositionAxisType.HEIGHT) -> Unit:
    lith = row.get("lithology")
    liths = vocab.liths(lith, LithAbundance.DOMINANT)
    # Process minor lithologies if they are present
    liths |= vocab.liths(row.get("minor_lith"), LithAbundance.SUBSIDIARY)
    environs = vocab.environs(row.get("environment"))

    unit = Unit(
        environment=environs,
        comments=row.get("comments"),
        b_pos=row["b_pos"],
        t_pos=row["t_pos"],
        description=row.get("description"),
        # A sheet may name a unit only by its formation.
        name=row.get("name") or row.get("strat_name"),
        lithology=liths,
        color=row.get("color"),
        row=row.get(ROW_COLUMN),
        outcrop=_outcrop(row.get("covered"), position),
    )

    # Only relative age positioning is supported for now
    with notices.notice_context(column="b_int"):
        b_int = get_interval_from_text(db, row.get("b_int"))
    if b_int is not None:
        unit.b_age = RelativeAge(
            interval=b_int, proportion=_proportion(row.get("b_prop"), 0, "b_prop")
        )

    with notices.notice_context(column="t_int"):
        t_int = get_interval_from_text(db, row.get("t_int"))
    if t_int is not None:
        unit.t_age = RelativeAge(
            interval=t_int, proportion=_proportion(row.get("t_prop"), 1, "t_prop")
        )
    return unit


def _outcrop(covered, position: PositionAxisType) -> str:
    if _truthy(covered):
        if position == PositionAxisType.DEPTH:
            notices.warning(
                "covered-on-depth-axis",
                "A covered unit on a depth axis: cores have no outcrop to be covered",
                column="covered",
            )
        return "covered"
    if position == PositionAxisType.DEPTH:
        return "subsurface"
    return "surface"


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("y", "yes", "true", "t", "1", "x")


def _proportion(value, default: float, column: str) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        proportion = float(value)
    except (TypeError, ValueError):
        notices.warning(
            "unreadable-proportion",
            f"`{column}` must be a number, got {value!r}; using {default}",
            column=column,
        )
        return default
    if not 0 <= proportion <= 1:
        clamped = min(max(proportion, 0), 1)
        notices.warning(
            "proportion-out-of-range",
            f"`{column}` must be between 0 and 1, got {proportion:g}; using {clamped:g}",
            column=column,
        )
        return clamped
    return proportion


def coalesce(value, default):
    if value is None:
        return default
    return value
