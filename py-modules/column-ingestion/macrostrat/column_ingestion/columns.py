from dataclasses import dataclass, field
from datetime import datetime

import polars as pl
from sqlalchemy.dialects.postgresql import insert

from macrostrat.database import Database

from .database import get_macrostrat_table
from .units import Unit


@dataclass
class Column:
    id: int = -1
    group_id: int = -1
    local_id: str | None = None
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    status_code: str = "in process"
    col_type: str = "column"
    geom: str | None = None
    rgeom: str | None = None
    units: list[Unit] = field(default_factory=list)


def get_or_create_column_group(db: Database, project_id: int, name="Default") -> int:
    """Get or create a column group for a given project ID."""
    col_groups_tbl = get_macrostrat_table(db, "col_groups")

    # TODO: need to add an index on project_id to the col_groups table for this to work properly

    # Find a pre-existing column group for the project, if it exists
    existing_group_id = (
        db.session.query(col_groups_tbl.c.id)
        .filter(col_groups_tbl.c.project_id == project_id)
        .filter(col_groups_tbl.c.col_group == name)
        .scalar()
    )
    if existing_group_id is not None:
        return existing_group_id

    insert_stmt = (
        insert(col_groups_tbl)
        .values(
            project_id=project_id,
            col_group="Default",
            col_group_long="Default column group",
        )
        .returning(col_groups_tbl.c.id)
    )
    return db.session.execute(insert_stmt).scalar()


def get_or_create_column(db: Database, col: Column) -> int:
    """Get or create a column in the database."""
    cols_tbl = get_macrostrat_table(db, "cols")

    # TODO: Use insert-on-conflict to get or create the column
    # Requires an index on (col_name, project_id) to work properly

    vals = dict(
        status_code=col.status_code,
        col_type=col.col_type,
        col_group_id=col.group_id,
    )

    default_vals = dict(
        # TODO: figure out how to handle these fields
        col_position="",
        col_area=0,
        created=datetime.now(),
        col=0,
        lat=0,
        lng=0,
    )

    # Get an existing column by name and project_id, if it exists
    col_id = (
        db.session.query(cols_tbl.c.id)
        .filter(cols_tbl.c.col_name == col.name)
        .filter(cols_tbl.c.project_id == col.project_id)
        .scalar()
    )
    stmt = None
    if col_id is not None:
        # Update the existing column with any new values
        print("Updating existing column with ID", col_id)
        stmt = (
            cols_tbl.update()
            .where(cols_tbl.c.id == col_id)
            .values(**vals)
            .returning(cols_tbl.c.id)
        )
    else:
        stmt = (
            insert(cols_tbl)
            .values(
                col_name=col.name,
                project_id=col.project_id,
                **default_vals,
                **vals,
            )
            .returning(cols_tbl.c.id)
        )
    return db.session.execute(stmt).scalar()


def get_or_create_section(db: Database, col_id: int) -> int:
    """Get a single section in the database for a given column ID, creating it if it doesn't exist.
    Note: multiple sections are not supported as yet.
    """
    sections_tbl = get_macrostrat_table(db, "sections")

    # Get an existing section for the column, if it exists
    section_id = (
        db.session.query(sections_tbl.c.id)
        .filter(sections_tbl.c.col_id == col_id)
        .scalar()
    )
    if section_id is not None:
        return section_id

    insert_stmt = (
        insert(sections_tbl)
        .values(col_id=col_id, fo=-1, fo_h=-1, lo=-1, lo_h=-1)
        .returning(sections_tbl.c.id)
    )

    return db.session.execute(insert_stmt).scalar()


def get_column_data(data_file, meta) -> list[Column]:
    df = pl.read_excel(data_file, sheet_name="columns")

    df = df.rename(
        {
            "name": "col_name",
            "id": "col_id",
            "type": "col_type",
        },
        strict=False,
    )

    print(df.head())

    columns = []
    for row in df.iter_rows(named=True):

        geom = row.get("rgeom", getattr(meta, "rgeom", None))

        col = Column(
            # TODO: implement ID upgrading to handle existing columns
            local_id=str(row.get("col_id")),
            name=row.get("col_name"),
            description=row.get("description"),
            status_code=row.get(
                "status_code", getattr(meta, "status_code", "in process")
            ),
            col_type=row.get("col_type", getattr(meta, "col_type", "column")),
            geom=row.get("geom"),
            rgeom=geom,
        )
        columns.append(col)
    return columns
