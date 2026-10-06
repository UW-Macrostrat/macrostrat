from datetime import date

from openpyxl import load_workbook

from macrostrat.core.database import get_database, set_audit_context
from macrostrat.database import on_conflict

from .age_model import build_age_model
from .columns import (
    Column,
    get_column_data,
    get_sections,
    reconcile_column_group,
    reconcile_columns,
    reconcile_sections,
)
from .database import ProjectIdentifier, get_or_create_project
from .metadata import get_metadata
from .refs import get_reference_data, reconcile_references, resolve_column_references
from .units import PositionAxisType, write_units


class _DryRunRollback(Exception):
    pass


def _age_fields(prefix: str, age) -> dict:
    if age is None:
        return {}
    return {
        f"{prefix}_int_id": age.interval.id,
        f"{prefix}_int_name": age.interval.name,
        f"{prefix}_prop": age.proportion,
        f"{prefix}_age": age.model_age(),
    }


def _preview_unit(unit) -> dict:
    """A unit in the v2 `/units?response=long` shape the web column editor loads."""
    notes = [n for n in (unit.description, unit.comments) if n]
    return {
        "unit_id": unit.id,
        "section_id": unit.section_id,
        # The column renderer string-matches unit names, so never send null.
        "unit_name": unit.name or "",
        "strat_name_long": unit.name,
        "b_pos": unit.b_pos,
        "t_pos": unit.t_pos,
        "color": unit.color,
        "notes": "\n".join(notes) or None,
        "lith": [
            {
                "lith_id": l.id,
                "name": l.name,
                "atts": sorted(a.name for a in (l.attributes or [])),
                "prop": l.prop,
            }
            for l in unit.lithology
        ],
        "environ": [{"environ_id": e.id, "name": e.name} for e in unit.environment],
        **_age_fields("b", unit.b_age),
        **_age_fields("t", unit.t_age),
    }


def _preview_columns(columns: list[Column]) -> list[dict]:
    """Parsed columns for the editor to render, so a dry run can be viewed unsaved."""
    return [
        {
            "columnInfo": {
                "col_name": col.name,
                "col_type": col.col_type,
                "axis_type": "height" if col.col_type == "section" else "age",
                "project_id": col.project_id,
            },
            "units": [_preview_unit(u) for u in col.units],
        }
        for col in columns
        if col.units
    ]


def ingest_columns_from_file(
    db,
    data_file,
    *,
    dry_run: bool = False,
) -> dict:
    # Get sheet names
    workbook = load_workbook(
        data_file, read_only=True, data_only=True, keep_links=False
    )
    sheet_names = workbook.sheetnames

    print(f"Sheets: {sheet_names}")

    if "units" not in sheet_names:
        raise ValueError("Sheet 'units' not found in the data file")

    meta = None
    project = None
    if "metadata" in sheet_names:
        meta = get_metadata(data_file)
        project = meta.project

    if "columns" in sheet_names:
        columns = get_column_data(data_file, meta)

    references = []
    if "refs" in sheet_names:
        references = get_reference_data(data_file)

    # Interpret positions as ordinal if the axis type is age
    position = PositionAxisType.HEIGHT
    if meta.axis_type == "age":
        position = PositionAxisType.ORDINAL

    sections = get_sections(
        db, data_file, position=position, fill_values=meta.fill_values
    )

    for col in columns:
        col.sections = sections.get(col.local_id, [])
        if len(col.units) == 0:
            print(f"Warning: No units found for column {col.local_id}")

    if project is None:
        raise ValueError("Project not found in the data file")

    return ingest_columns(
        db, columns, project=project, references=references, dry_run=dry_run
    )


def ingest_columns(
    db,
    columns: list[Column],
    *,
    project: ProjectIdentifier,
    references: list | None = None,
    dry_run: bool = False,
):
    """Write columns, their sections, their units and their age models.

    Takes `Column` objects with `sections` already populated, which is the seam a
    caller needs when its data did not come from a workbook. The spreadsheet is one
    source of columns, not the only one: GBDB yields ~29,000 columns from a
    relational staging schema, and routing those through an .xlsx to reach this
    sequence would be absurd. `ingest_columns_from_file` is now the spreadsheet
    front-end to this function.
    """
    # One transaction for the whole (column, sections, units) set, so `units.section_id`
    # can reference sections that are created in the same breath — the constraint the
    # legacy importer had to drop because it could not precalculate sections.
    try:
        with db.transaction(), on_conflict("restrict"):
            print(f"Ingesting data into project: {project.name}")
            _project = get_or_create_project(db, project)

            # Attribute everything below in the change-tracking trail. Transaction-local
            # is right here (unlike the rebuild scripts): every audited write in this
            # function — col_groups, cols, sections, units, and the unit_boundaries the
            # age model writes — happens inside this one transaction. Set after the
            # project is resolved so the batch can name it; `projects` is not audited,
            # so nothing captured is missed by setting it here rather than earlier.
            set_audit_context(
                db,
                "system:column-ingest",
                f"ingest:{_project.slug}:{date.today().isoformat()}",
            )

            col_group_id = reconcile_column_group(db, _project.id)

            # References come first: columns cite them, and the citations are resolved from
            # workbook-local ids once the reference rows exist.
            ref_map = reconcile_references(db, references or [])

            reconcile_columns(
                db, columns, project_id=_project.id, col_group_id=col_group_id
            )
            if ref_map:
                resolve_column_references(db, columns, ref_map)

            for col in columns:
                if not col.units:
                    continue
                print(f"Ingesting column: {col.name}, ID: {col.id}")
                # Sections first, so every unit is written against a section that exists.
                reconcile_sections(db, col.id, col.sections)
                write_units(db, col.sections)
                build_age_model(db, col.units)

            # Capture the summary before committing/rolling back, while the ORM
            # objects are still live (a rollback would expire them).
            summary = {
                "project": {
                    "id": _project.id,
                    "slug": _project.slug,
                    "name": project.name,
                },
                "col_group_id": col_group_id,
                "n_columns": len(columns),
                "n_units": sum(len(col.units) for col in columns),
                "n_references": len(references or []),
                "dry_run": dry_run,
                "columns": _preview_columns(columns),
            }

            if dry_run:
                raise _DryRunRollback
            return summary
    except _DryRunRollback:
        print("Dry run — transaction rolled back; nothing was persisted.")
        return summary
