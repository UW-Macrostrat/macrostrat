"""Graded data-quality notices, collected while a column dataset is parsed and written.

An ingest used to report problems through a mix of `print`, logging, bare `assert`s
and exceptions, so the first bad cell aborted the run and everything else stayed
unseen. Notices replace that: every check reports a `Notice` with a level — `info`,
`warning` or `error` — to the collector active in the current context, and the run
decides at the end what the errors mean (a dry run returns them; a write refuses to
proceed). Callers outside a collecting context see the old behaviour, so the parsers
can still be used one cell at a time.

Levels
------
- **error** — the data cannot be written as it stands (an unknown environment, a column
  with no location, a unit whose base is younger than its top).
- **warning** — the data will be written but is probably not what the author meant (a
  lithology word Macrostrat does not know, a measured section with only a polygon).
- **info** — something the author should know happened (rows dropped, values filled).

Each notice carries where it applies: the sheet, the row, the column, the column id
and unit name when known. `notice_context` sets the defaults for everything reported
within it, so a parser deep in a section does not have to be handed them.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterator

from macrostrat.utils import get_logger

log = get_logger(__name__)


class Level(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


#: Where a notice applies. Every field is optional.
LOCATION_FIELDS = ("sheet", "row", "column", "col_id", "unit", "section")


@dataclass
class Notice:
    level: Level
    #: A stable, kebab-case identifier for the check (`unknown-environment`), so a
    #: client can group, filter or document notices without parsing messages.
    code: str
    message: str
    sheet: str | None = None
    #: The spreadsheet row (1-based, header included), when the notice is about one.
    row: int | None = None
    #: The spreadsheet column (field name), when the notice is about one.
    column: str | None = None
    #: The workbook-local column id the notice applies to.
    col_id: str | None = None
    unit: str | None = None
    section: str | None = None
    #: Anything else a check wants to pass along (the offending values, say).
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["level"] = self.level.value
        return {k: v for k, v in out.items() if v not in (None, {}, [])}


class Notices:
    """The notices of one run."""

    def __init__(self):
        self.items: list[Notice] = []

    def add(self, notice: Notice) -> Notice:
        self.items.append(notice)
        return notice

    def __iter__(self) -> Iterator[Notice]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def at_level(self, level: Level) -> list[Notice]:
        return [n for n in self.items if n.level is level]

    @property
    def errors(self) -> list[Notice]:
        return self.at_level(Level.ERROR)

    @property
    def warnings(self) -> list[Notice]:
        return self.at_level(Level.WARNING)

    @property
    def has_errors(self) -> bool:
        return any(n.level is Level.ERROR for n in self.items)

    def to_list(self) -> list[dict]:
        return [n.to_dict() for n in self.items]

    def summary(self) -> dict[str, int]:
        return {level.value: len(self.at_level(level)) for level in Level}


_collector: ContextVar[Notices | None] = ContextVar("notices", default=None)
_context: ContextVar[dict] = ContextVar("notice_context", default={})


def current_notices() -> Notices | None:
    """The collector active in this context, or `None` outside a collecting run."""
    return _collector.get()


@contextmanager
def collect_notices(notices: Notices | None = None) -> Iterator[Notices]:
    """Collect every notice reported within the block."""
    if notices is None:
        notices = Notices()
    token = _collector.set(notices)
    try:
        yield notices
    finally:
        _collector.reset(token)


@contextmanager
def notice_context(**where) -> Iterator[None]:
    """Default location fields for notices reported within the block."""
    merged = {**_context.get(), **{k: v for k, v in where.items() if v is not None}}
    token = _context.set(merged)
    try:
        yield
    finally:
        _context.reset(token)


def report(level: Level, code: str, message: str, **where) -> Notice | None:
    """Report a notice to the active collector.

    Returns the notice, or `None` when nothing is collecting — the signal a caller
    uses to fall back to raising, so a parser used on its own still fails loudly.
    """
    detail = where.pop("detail", None) or {}
    location = {**_context.get()}
    for key, value in where.items():
        if key not in LOCATION_FIELDS:
            raise TypeError(f"Unknown notice field {key!r}")
        if value is not None:
            location[key] = value
    notice = Notice(level=level, code=code, message=message, detail=detail, **location)

    log_fn = {Level.ERROR: log.error, Level.WARNING: log.warning}.get(level, log.info)
    log_fn("%s: %s", code, message)

    collector = _collector.get()
    if collector is None:
        return None
    return collector.add(notice)


def info(code: str, message: str, **where) -> Notice | None:
    return report(Level.INFO, code, message, **where)


def warning(code: str, message: str, **where) -> Notice | None:
    return report(Level.WARNING, code, message, **where)


def error(code: str, message: str, **where) -> Notice | None:
    return report(Level.ERROR, code, message, **where)


def error_or_raise(exc: Exception, code: str, **where) -> None:
    """Report `exc` as an error notice, or raise it when nothing is collecting."""
    if report(Level.ERROR, code, str(exc), **where) is None:
        raise exc


class IngestValidationError(ValueError):
    """The dataset has error-level notices and cannot be written as it stands."""

    def __init__(self, notices: Notices):
        self.notices = notices
        errors = notices.errors
        lines = [f"{n.code}: {n.message}" for n in errors[:10]]
        if len(errors) > 10:
            lines.append(f"... and {len(errors) - 10} more")
        super().__init__(
            f"{len(errors)} error(s) in the column data:\n  " + "\n  ".join(lines)
        )
