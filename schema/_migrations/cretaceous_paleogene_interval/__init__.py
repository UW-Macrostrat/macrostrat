from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists


def _named(name: str, top: str, bottom: str):
    """An interval called `name` spans from the top of `top` to the base of `bottom`."""

    def condition(db: Database) -> bool:
        return db.run_query(
            """
            SELECT EXISTS (
              SELECT 1 FROM macrostrat.intervals i
              JOIN macrostrat.intervals t ON t.interval_name = :top
              JOIN macrostrat.intervals b ON b.interval_name = :bottom
              WHERE i.interval_name = :name
                AND i.age_top = t.age_top AND i.age_bottom = b.age_bottom
            )
            """,
            dict(name=name, top=top, bottom=bottom),
        ).scalar()

    condition.__name__ = f"interval {name!r} spans {top} to {bottom}"
    return condition


class CretaceousPaleogeneIntervalMigration(Migration):
    name = "cretaceous-paleogene-interval"
    subsystem = "core"
    description = """
    Rename the Late Cretaceous–Paleocene composite interval, which was called
    Cretaceous-Paleogene, and add a Cretaceous-Paleogene spanning both periods.
    """
    readiness_state = "ga"
    destructive = True

    preconditions = [exists("macrostrat", "intervals")]
    postconditions = [
        _named("Late Cretaceous-Paleogene", "Paleocene", "Late Cretaceous"),
        _named("Cretaceous-Paleogene", "Paleogene", "Cretaceous"),
    ]
