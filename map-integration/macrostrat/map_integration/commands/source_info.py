from psycopg2.sql import Identifier

from ..database import db
from ..utils import MapInfo, feature_counts, get_map_info, table_exists


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
    counts = feature_counts(info)
    print(f"Polygons: {counts.n_polygons}")
    print(f"Lines: {counts.n_lines}")
    print(f"Points: {counts.n_points}")
