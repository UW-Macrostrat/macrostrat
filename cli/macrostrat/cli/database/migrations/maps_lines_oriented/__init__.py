"""
Macrostrat line orientation management
"""

from macrostrat.database import Database

from macrostrat.core.migrations import Migration, has_columns

_has_column = has_columns("maps", "sources", "lines_oriented")


class MapsLinesOriented(Migration):
    name = "maps-lines-oriented"
    subsystem = "maps"
    description = "Create a flag for line orientations in maps.sources table."

    depends_on = ["baseline", "map-source-slug"]

    postconditions = [_has_column]

    def apply(self, db: Database):
        db.run_sql("ALTER TABLE maps.sources ADD COLUMN lines_oriented boolean")


# Legacy maps with consistently-oriented linework that needs to be reversed
valid_maps = [229, 210, 74, 75, 40, 205, 154]

# Legacy maps with consistently-oriented linework that does not need to be reversed
reversed_maps = [4]
# Note: we have flipped the logic here relative to how we did this in the original iteration
# of the system, to aloign with FGDC recommendations (we think)


def matching_sources(
    db: Database, sources: list[int], condition: str = "true"
) -> list[int]:
    return list(
        db.run_query(
            f"SELECT source_id FROM maps.sources WHERE source_id = ANY(:sources) AND {condition}",
            dict(sources=sources),
        ).scalars()
    )


def some_maps_are_unoriented(db: Database) -> bool:
    if not _has_column(db):
        return False
    ids = matching_sources(
        db, valid_maps + reversed_maps, "NOT coalesce(lines_oriented, false)"
    )
    return len(ids) > 0


def all_maps_are_oriented(db: Database) -> bool:
    if not _has_column(db):
        return False
    _all_maps = valid_maps + reversed_maps
    ids = matching_sources(db, _all_maps, "coalesce(lines_oriented, false)")
    return len(ids) == len(_all_maps)


class MapsLinesOrientedDataMigration(Migration):
    name = "maps-lines-oriented-data"
    subsystem = "maps"
    depends_on = ["maps-lines-oriented"]

    destructive = True

    preconditions = [some_maps_are_unoriented]
    postconditions = [all_maps_are_oriented]

    def apply(self, db: Database):
        # Get the maps that aren't oriented but appear in our list of maps to migrate
        all_maps = valid_maps + reversed_maps
        unoriented_maps = matching_sources(
            db, all_maps, "NOT coalesce(lines_oriented, false)"
        )
        for source_id in unoriented_maps:
            if source_id in reversed_maps:
                db.run_sql(
                    "UPDATE maps.lines SET geom = ST_Reverse(geom) WHERE source_id = :source_id",
                    dict(source_id=source_id),
                )
            db.run_sql(
                "UPDATE maps.sources SET lines_oriented = true WHERE source_id = :source_id",
                dict(source_id=source_id),
            )
