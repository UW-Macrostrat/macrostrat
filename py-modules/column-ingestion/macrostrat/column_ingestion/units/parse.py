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


#: The original spreadsheet row of each unit row, carried through sorting and grouping.
ROW_COLUMN = "_row"


def prepare_section_units(
    db,
    df,
    *,
    position: PositionAxisType = PositionAxisType.HEIGHT,
    fill_values: bool = True,
    vocab=None,
) -> list[Unit]:
    """The rows of one section as `Unit`s.

    `vocab` is the run's `Vocabulary` (lithology and environment processors); one is
    built here when a caller has none, at the cost of a lookup fetch.
    """
    if vocab is None:
        from ..vocabulary import Vocabulary

        vocab = Vocabulary(db)
    # Sort by b_pos (descending if height)
    # TODO: figure out how to switch conventions for depth
    df = df.sort("b_pos", descending=True)

    # Fill in t_pos with the next b_pos value, unless it already exists
    # Do the same for intervals and proportions
    for suffix in ["pos", "prop", "int"]:
        b_col = "b_" + suffix
        t_col = "t_" + suffix
        # If the t_pos column does not exist, create it (empty for now)

        for col in [b_col, t_col]:
            if col in df.columns:
                continue
            df = df.with_columns(pl.lit(None, float).alias(col))

        # Create a column with default values for the top position of each unit
        _t_col = df[b_col].shift(1)

        if position == PositionAxisType.ORDINAL and t_col == "t_pos":
            # If ordinal, set the top position to the bottom position + 1 where it is unset
            _t_col = pl.when(_t_col.is_null()).then(df[b_col] + 1).otherwise(_t_col)

        df = df.with_columns(
            pl.when(pl.col(t_col).is_null())
            .then(_t_col)
            .otherwise(pl.col(t_col))
            .alias(t_col)
        )

    # Rows without both positions cannot be placed; say which, then drop them
    unplaced = df.filter(df["t_pos"].is_null() | df["b_pos"].is_null())
    for row in unplaced.iter_rows(named=True):
        notices.warning(
            "unit-missing-position",
            f"Unit {row.get('name') or ''!r} has no bottom or top position and was "
            "left out",
            row=row.get(ROW_COLUMN),
            unit=row.get("name"),
            column="b_pos",
        )
    df = df.filter((df["t_pos"].is_not_null()) & (df["b_pos"].is_not_null()))

    fill_specs = [
        "lithology",
        "minor_lith",
        "color",
        "grainsize",
        "strat_name",
        "facies",
        "name",
    ]
    for spec in fill_specs:
        if not fill_values:
            continue
        if spec not in df.columns:
            continue
        new_col = df[spec].fill_null(strategy="forward").alias(spec)
        # Cast the new column to a string
        new_col = new_col.cast(pl.Utf8)
        df = df.with_columns(new_col)
        # Fill 'none' values in the new column with nulls
        df = df.with_columns(
            pl.when(pl.col(spec) == "none")
            .then(pl.lit(None))
            .otherwise(pl.col(spec))
            .alias(spec)
        )

    res = []
    for row in df.iter_rows(named=True):
        with notices.notice_context(row=row.get(ROW_COLUMN), unit=row.get("name")):
            res.append(_unit_from_row(db, row, vocab))

    return res


def _unit_from_row(db, row: dict, vocab) -> Unit:
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


def _proportion(value, default: float, column: str) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        proportion = float(value)
    except (TypeError, ValueError):
        notices.error(
            "unreadable-proportion",
            f"`{column}` must be a number, got {value!r}",
            column=column,
        )
        return default
    if not 0 <= proportion <= 1:
        notices.error(
            "proportion-out-of-range",
            f"`{column}` must be between 0 and 1, got {proportion:g}",
            column=column,
        )
    return proportion


def coalesce(value, default):
    if value is None:
        return default
    return value
