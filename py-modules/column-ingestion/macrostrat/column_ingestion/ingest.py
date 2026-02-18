from macrostrat.core.database import get_database
from openpyxl import load_workbook

from .columns import get_column_data
from .database import get_or_create_project
from .metadata import get_metadata
from .units import get_units


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

    if "columns" in sheet_names:
        columns = get_column_data(data_file, meta)

    units = get_units(data_file)
    for col in columns:
        col.units = units.get(col.local_id, [])
        if len(col.units) == 0:
            print(f"Warning: No units found for column {col.local_id}")

    db = get_database()
    # Start ingesting the data into the database, using the project information if available
    if project is not None:
        print(f"Ingesting data for project: {project.name}")
        _project = get_or_create_project(db, project)
        print("Project", _project.id, _project.slug)
