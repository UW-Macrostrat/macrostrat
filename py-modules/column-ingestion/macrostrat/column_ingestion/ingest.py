from macrostrat.core.database import get_database
from macrostrat.database import on_conflict
from openpyxl import load_workbook

from .columns import (
    get_column_data,
    get_or_create_column,
    get_or_create_section,
    get_or_create_column_group,
)
from .database import get_or_create_project
from .metadata import get_metadata
from .units import get_units, write_units


def ingest_columns_from_file(data_file):
    # Get sheet names
    workbook = load_workbook(data_file, read_only=True)
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

    units = get_units(data_file)

    for col in columns:
        col.units = units.get(col.local_id, [])
        if len(col.units) == 0:
            print(f"Warning: No units found for column {col.local_id}")

    db = get_database()
    if project is None:
        raise ValueError("Project not found in the data file")

    # Start ingesting the data into the database, using the project information if available
    with db.transaction(), on_conflict("restrict"):
        print(f"Ingesting data into project: {project.name}")
        _project = get_or_create_project(db, project)
        col_group_id = get_or_create_column_group(db, _project.id)
        print("Project", _project.id, _project.slug)
        for col in columns:
            col.project_id = _project.id
            col.group_id = col_group_id
            col_id = get_or_create_column(db, col)
            print(f"Ingesting column: {col.name}, ID: {col_id}")
            col.id = col_id
            # Create a section for the column (if it doesn't already exist)
            section_id = get_or_create_section(db, col_id)
            print(f"Section ID: {section_id}")

            # Sync the units with the column ID
            for unit in col.units:
                unit.col_id = col_id
                unit.section_id = section_id
            write_units(db, col.units)
        db.session.commit()
