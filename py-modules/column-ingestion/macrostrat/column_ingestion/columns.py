from dataclasses import dataclass, field

import polars as pl
from macrostrat.database import Database

from .database import get_macrostrat_model
from .units import Unit


@dataclass
class Column:
    id: int = -1
    local_id: str | None = None
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    status_code: str = "in process"
    col_type: str = "column"
    geom: str | None = None
    rgeom: str | None = None
    units: list[Unit] = field(default_factory=list)


def get_or_create_column(db: Database, col: Column) -> Column:
    """Get or create a column in the database."""
    Cols = get_macrostrat_model(db, "cols")

    # Use insert-on-conflict to get or create the column

    insert_stmt = (
        Cols.__table__.insert()
        .values(
            name=col.name,
            description=col.description,
            project_id=col.project_id,
            status_code=col.status_code,
            col_type=col.col_type,
            geom=col.geom,
        )
        .on_conflict_do_update(index_elements=["name", "project_id"])
        .returning(Cols.col_id)
    )

    col_id = db.session.execute(insert_stmt).scalar()
    col.id = col_id
    return col


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
