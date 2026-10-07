"""Ingesting a column dataset: parse, check, write — or check and show.

A dataset arrives as a set of named tables in the column-ingestion format: the sheets
of a workbook (`ingest_columns_from_file`), or the same tables as JSON from an editor
(`ingest_column_data`). Both go through `ingest_sheets`:

1. **Parse** every sheet into `Column`, `Section`, `Unit` and `Reference`
   objects, resolving vocabularies against the database. Nothing is written.
2. **Check** the parsed dataset (`validation`). Every problem found so far is a
   `Notice`; an error-level notice means the data cannot be written as it stands.
3. **Write** inside one transaction (`ingest_columns`), then read the result back as
   the web API would serve it (`payload`). A **dry run** does all of that and rolls the
   transaction back, so the result shows exactly what the database would hold.

The result is one JSON-serialisable dict, whatever the path in:

    {
      "dry_run": bool,
      "ok": bool,                # no error-level notices
      "summary": {...} | None,   # project, column group, counts — None if not written
      "notices": [...],          # every notice, graded
      "notice_counts": {"info": n, "warning": n, "error": n},
      "data": {...} | None,      # columns, units, boundaries — the editor's view
    }
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import polars as pl
from openpyxl import load_workbook

from macrostrat.core.database import set_audit_context
from macrostrat.database import on_conflict
from macrostrat.utils import get_logger

from . import notices
from .age_model import build_age_model
from .columns import (
    Column,
    columns_from_df,
    get_sections_from_df,
    reconcile_column_group,
    reconcile_columns,
    reconcile_sections,
)
from .database import ProjectIdentifier, get_or_create_project
from .metadata import (
    Metadata,
    metadata_from_df,
    metadata_from_dict,
    read_metadata_sheet,
)
from .notices import IngestValidationError, Notices
from .payload import build_payload
from .refs import (
    Reference,
    reconcile_references,
    references_from_df,
    resolve_column_references,
)
from .units import PositionAxisType, write_units
from .validation import validate_dataset
from .vocabulary import Vocabulary

log = get_logger(__name__)


class _DryRunRollback(Exception):
    pass


#: The sheets the format defines. Anything else is a column-linked data sheet, which
#: is carried along but not interpreted here.
CORE_SHEETS = ("metadata", "columns", "units", "refs", "facies", "images")


@dataclass
class ParsedDataset:
    """A dataset's tables, parsed and resolved, before anything is written."""

    metadata: Metadata
    project: ProjectIdentifier | None
    columns: list[Column]
    references: list[Reference] = field(default_factory=list)


# ------------------------------------------------------------------ reading


def read_workbook(data_file) -> dict[str, pl.DataFrame]:
    """Every sheet of a workbook as a data frame, by sheet name."""
    workbook = load_workbook(
        data_file, read_only=True, data_only=True, keep_links=False
    )
    sheets: dict[str, pl.DataFrame] = {}
    for name in workbook.sheetnames:
        if name == "metadata":
            sheets[name] = read_metadata_sheet(data_file)
        else:
            sheets[name] = pl.read_excel(data_file, sheet_name=name)
    return sheets


def sheets_from_data(data: dict) -> dict[str, pl.DataFrame]:
    """The format's tables from JSON: `{sheet: [row, ...]}`, metadata as a dict."""
    sheets: dict[str, pl.DataFrame] = {}
    for name, table in data.items():
        if table is None:
            continue
        if name == "metadata" and isinstance(table, dict):
            sheets[name] = pl.DataFrame(
                {"key": list(table.keys()), "value": [_cell(v) for v in table.values()]}
            )
            continue
        if isinstance(table, list):
            if len(table) == 0:
                continue
            # Everything as text, as a spreadsheet cell would arrive; the parsers cast.
            rows = [{k: _cell(v) for k, v in row.items()} for row in table]
            sheets[name] = pl.DataFrame(rows, infer_schema_length=None)
    return sheets


def _cell(value):
    """A JSON value as spreadsheet text. Everything is text so a column that mixes
    numbers and words (a `col_id` of `9999` beside one of `A1`) still forms a frame;
    the parsers cast what they need."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return "; ".join(str(v) for v in value)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


# ------------------------------------------------------------------ parsing


def parse_sheets(db, sheets: dict[str, pl.DataFrame]) -> ParsedDataset:
    """Parse and resolve a dataset's tables. Reports problems as notices."""
    if "metadata" in sheets:
        meta = metadata_from_df(sheets["metadata"])
    else:
        notices.warning(
            "missing-sheet",
            "No `metadata` sheet; assuming a composite column with ages as the axis",
            sheet="metadata",
        )
        meta = metadata_from_dict({})

    vocab = Vocabulary(db)

    references: list[Reference] = []
    if "refs" in sheets:
        references = references_from_df(sheets["refs"])

    if "columns" in sheets:
        columns = columns_from_df(sheets["columns"], meta)
    else:
        notices.warning(
            "missing-sheet",
            "No `columns` sheet; a single column is assumed, without metadata",
            sheet="columns",
        )
        columns = [
            Column(
                local_id="1",
                name=_text(getattr(meta, "project", None) and meta.project.name)
                or "Column 1",
                col_type=meta.col_type,
                axis_type=meta.axis_type,
                rgeom=meta.rgeom,
            )
        ]

    if "units" not in sheets:
        notices.error("missing-sheet", "No `units` sheet", sheet="units")
        return ParsedDataset(meta, meta.project, columns, references)

    # Interpret positions as ordinal if the axis type is age
    position = PositionAxisType.HEIGHT
    if meta.axis_type == "age":
        position = PositionAxisType.ORDINAL
    elif meta.axis_type == "depth":
        position = PositionAxisType.DEPTH

    sections = get_sections_from_df(
        db,
        sheets["units"],
        position=position,
        fill_values=meta.fill_values,
        vocab=vocab,
    )

    known = {col.local_id for col in columns}
    for local_id in sections:
        if local_id not in known:
            notices.error(
                "unit-without-column",
                f"Units refer to column {local_id!r}, which the columns sheet does not "
                "define",
                sheet="units",
                col_id=local_id,
            )
    for col in columns:
        col.sections = sections.get(col.local_id, [])

    return ParsedDataset(meta, meta.project, columns, references)


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# ------------------------------------------------------------------ entry points


def ingest_columns_from_file(db, data_file, *, dry_run: bool = False) -> dict:
    """Ingest a workbook in the column-ingestion format. See the module docstring."""
    return ingest_sheets(db, read_workbook(data_file), dry_run=dry_run)


def ingest_column_data(db, data: dict, *, dry_run: bool = False) -> dict:
    """Ingest the format's tables given as JSON, as an editor submits them."""
    return ingest_sheets(db, sheets_from_data(data), dry_run=dry_run)


def ingest_sheets(
    db, sheets: dict[str, pl.DataFrame], *, dry_run: bool = False
) -> dict:
    with notices.collect_notices() as collected:
        dataset = parse_sheets(db, sheets)
        validate_dataset(dataset.columns)

        project = dataset.project
        if project is None:
            notices.error(
                "no-project",
                "No project: the metadata needs a `project_id`, `project_slug` or "
                "`project_name`",
                sheet="metadata",
            )

        if collected.has_errors and not dry_run:
            raise IngestValidationError(collected)
        if project is None:
            return _result(dry_run, collected, None, None)

        return ingest_columns(
            db,
            dataset.columns,
            project=project,
            references=dataset.references,
            dry_run=dry_run,
            notices_=collected,
        )


def ingest_columns(
    db,
    columns: list[Column],
    *,
    project: ProjectIdentifier,
    references: list | None = None,
    dry_run: bool = False,
    notices_: Notices | None = None,
) -> dict:
    """Write columns, their sections, their units and their age models.

    Takes `Column` objects with `sections` already populated, which is the seam a
    caller needs when its data did not come from a workbook. The spreadsheet is one
    source of columns, not the only one: GBDB yields ~29,000 columns from a
    relational staging schema, and routing those through an .xlsx to reach this
    sequence would be absurd. `ingest_sheets` is the tabular front-end to this function.

    On a dry run the writes happen and are read back, then rolled back; a failure
    during the write becomes an error notice rather than an exception, so the caller
    still gets every notice gathered so far.
    """
    with notices.collect_notices(notices_) as collected:
        summary = None
        payload = None
        # One transaction for the whole (column, sections, units) set, so
        # `units.section_id` can reference sections that are created in the same
        # breath — the constraint the legacy importer had to drop because it could not
        # precalculate sections.
        try:
            with db.transaction(), on_conflict("restrict"):
                try:
                    summary, payload = _write(
                        db, columns, project, references or [], dry_run
                    )
                except Exception as err:
                    if not dry_run:
                        raise
                    log.exception("dry run: write failed")
                    notices.error(
                        "write-failed",
                        f"Writing the data failed: {_describe(err)}",
                        detail={"type": type(err).__name__},
                    )
                if dry_run:
                    raise _DryRunRollback
        except _DryRunRollback:
            log.info("Dry run — transaction rolled back; nothing was persisted.")
        return _result(dry_run, collected, summary, payload)


def _write(db, columns, project, references, dry_run):
    log.info("Ingesting data into project: %s", project.name)
    _project = get_or_create_project(db, project)

    # Attribute everything below in the change-tracking trail. Transaction-local is
    # right here (unlike the rebuild scripts): every audited write in this function —
    # col_groups, cols, sections, units, and the unit_boundaries the age model writes —
    # happens inside this one transaction. Set after the project is resolved so the
    # batch can name it; `projects` is not audited, so nothing captured is missed by
    # setting it here rather than earlier.
    set_audit_context(
        db,
        "system:column-ingest",
        f"ingest:{_project.slug}:{date.today().isoformat()}",
    )

    col_group_id = reconcile_column_group(db, _project.id)

    # References come first: columns cite them, and the citations are resolved from
    # workbook-local ids once the reference rows exist.
    ref_map = reconcile_references(db, references)

    reconcile_columns(db, columns, project_id=_project.id, col_group_id=col_group_id)
    if ref_map:
        resolve_column_references(db, columns, ref_map)

    for col in columns:
        if not col.units:
            notices.warning(
                "no-units", f"Column {col.name!r} has no units", col_id=col.local_id
            )
            continue
        log.info("Ingesting column: %s, ID: %s", col.name, col.id)
        with notices.notice_context(col_id=col.local_id):
            # Sections first, so every unit is written against a section that exists.
            reconcile_sections(db, col.id, col.sections)
            write_units(db, col.sections)
            plans = build_age_model(db, col.units)
            if not plans:
                notices.warning(
                    "no-age-model-written",
                    f"Column {col.name!r}: no age model could be built, so its units "
                    "carry no modeled ages",
                )

    summary = {
        "project": {"id": _project.id, "slug": _project.slug, "name": _project.name},
        "col_group_id": col_group_id,
        "columns": [{"col_id": col.id, "col_name": col.name} for col in columns],
        "n_columns": len(columns),
        "n_units": sum(len(col.units) for col in columns),
        "n_references": len(references),
        "dry_run": dry_run,
    }
    # Read back while the rows are still there (a rollback would expire them)
    payload = build_payload(db, columns, provisional=dry_run)
    return summary, payload


def _describe(err: Exception) -> str:
    text = str(err).strip().splitlines()
    return text[0] if text else type(err).__name__


def _result(dry_run: bool, collected: Notices, summary, payload) -> dict:
    return {
        "dry_run": dry_run,
        "ok": not collected.has_errors,
        "summary": summary,
        "notices": collected.to_list(),
        "notice_counts": collected.summary(),
        "data": payload,
    }
