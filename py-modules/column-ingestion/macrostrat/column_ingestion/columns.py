from dataclasses import dataclass

from macrostrat.database import Database

from .database import get_macrostrat_model
from .lithologies import Lithology


@dataclass
class Column:
    id: int
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    status_code: str = "in process"
    col_type: str = "column"
    geom: str | None = None

@dataclass
class Unit:
    id: int
    col_id: int
    section_id: str | None = None
    b_pos: float | None = None
    t_pos: float | None = None
    lithology: set[Lithology] | None = None
    description: str | None = None
    name: str | None = None


def get_or_create_column(db: Database, col: Column) -> Column:
    """Get or create a column in the database."""
    Cols = get_macrostrat_model(db, "cols")

    # Use insert-on-conflict to get or create the column

    insert_stmt = Cols.__table__.insert().values(
        name=col.name,
        description=col.description,
        project_id=col.project_id,
        status_code=col.status_code,
        col_type=col.col_type,
        geom=col.geom,
    ).on_conflict_do_update(
        index_elements=["name", "project_id"]
    ).returning(Cols.col_id)

    col_id = db.session.execute(insert_stmt).scalar()
    col.id = col_id
    return col



