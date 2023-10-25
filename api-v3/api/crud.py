from sqlalchemy.orm import Session

from macrostrat.map_integration.database import db as macrostrat_db
from macrostrat.map_integration.api import models

def get_polygons(db: Session, source_id: str, skip: int = 0, limit: int = 100):
    db.query(macrostrat_db.models)


if __name__ == "__main__":
    get_polygons(macrostrat_db.session, "test_id")