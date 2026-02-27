from pathlib import Path

from macrostrat.core.database import get_database

from ..base import Base
from .lookup_units import copy_table_into_place

here = Path(__file__).parent


def _lookup_unit_attrs_api(db):
    """V2 CLI handler for lookup_unit_attrs_api."""
    db.run_sql(here / "sql" / "lookup-unit-attrs-api-01.sql")
    validate_counts(db)
    copy_table_into_place(db, "lookup_unit_attrs_api")


def validate_counts(db):
    data = db.run_query(
        "SELECT COUNT(*) units_count, (SELECT COUNT(*) FROM lookup_unit_attrs_api_new) lookup_units_count FROM units"
    ).fetchone()
    if data.units_count != data.lookup_units_count:
        raise ValueError(
            "Inconsistent units count in lookup_unit_attrs_api_new table", data
        )
    else:
        print(
            f"""Validation successful:
units:                 {data.units_count} rows
lookup_unit_attrs_api: {data.lookup_units_count} rows
"""
        )


class LookupUnitsAttrsAPI(Base):
    def __init__(self, *args):
        Base.__init__(self, {}, *args)

    def run(self):
        db = get_database()
        _lookup_unit_attrs_api(db)
