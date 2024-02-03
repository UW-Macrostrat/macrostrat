from psycopg2.sql import Identifier

from ..database import db
from ..utils import get_map_info, table_exists


def source_info(identifier: str):
    """Get information about a map source."""

    info = get_map_info(db, identifier)

    print(f"ID: {info.id}")
    print(f"Slug: {info.slug}")

    # Check table contents

    for table in ["polygons", "lines", "points"]:
        table_name = f"{info.slug}_{table}"
        exists = table_exists(db, table_name, schema="sources")
        print(f"{table_name}: {exists}")
        identifier = Identifier("sources", table_name)

        # Get count of rows and readiness state
        if exists:
            res = db.run_query(
                "SELECT count(*), sum((coalesce(omit, false) = true)::int) omitted FROM {table_name}",
                dict(table_name=identifier),
            ).one()
            print(f"  Rows: {res.count}")
            if res.omitted > 0:
                print(f"  Omitted: {res.omitted}")
    print()

    # Get info in maps schema
    print("Maps schema info")
    for table in ["polygons", "lines", "points"]:
        table_name = Identifier("maps", table)
        res = db.run_query(
            "SELECT count(*) FROM {table_name} WHERE source_id = :source_id",
            dict(table_name=table_name, source_id=info.id),
        ).one()

        print(f"maps.{table}: {res.count}")
