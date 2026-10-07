from collections import defaultdict

from psycopg2.sql import Identifier

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database
from macrostrat.map_integration.utils import MapInfo
from macrostrat.map_utils.slugs import (
    SLUG_PATTERN,
    STAGING_KINDS,
    slugify,
    table_prefix,
)
from macrostrat.schema_management import Migration, _not, has_columns

CONSTRAINT = "sources_slug_kebab"


def _has_constraint(db: Database) -> bool:
    found = db.run_query(
        "SELECT 1 FROM pg_constraint WHERE conname = :name"
        " AND conrelid = 'maps.sources'::regclass",
        dict(name=CONSTRAINT),
    )
    return found.first() is not None


class MapSourceKebabSlugsMigration(Migration):
    name = "map-source-kebab-slugs"
    owner = None  # renames staging tables, whoever owns them
    subsystem = "maps"
    description = """
    Rewrite every map source slug in kebab-case, rename staging tables to the
    underscore prefix derived from it, drop the redundant ingest_process.slug,
    and enforce the form with a check constraint.
    """
    depends_on = ["map-source-slug"]
    readiness_state = "alpha"
    destructive = True

    preconditions = [has_columns("maps", "sources", "slug")]
    postconditions = [
        _not(has_columns("maps_metadata", "ingest_process", "slug")),
        _has_constraint,
    ]

    def apply(self, db: Database):
        rows = db.run_query("SELECT source_id, slug FROM maps.sources").all()
        renamed = {r.slug: slugify(r.slug) for r in rows}
        _refuse_collisions(rows, renamed)

        tables = set(
            db.run_query(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = 'sources'"
            ).scalars()
        )

        db.run_sql(
            """
            ALTER TABLE maps_metadata.ingest_process DROP COLUMN IF EXISTS slug CASCADE;
            CREATE OR REPLACE VIEW macrostrat_api.map_ingest AS
              SELECT * FROM maps_metadata.ingest_process;
            GRANT SELECT, UPDATE ON macrostrat_api.map_ingest TO web_user, web_admin;
            GRANT SELECT ON macrostrat_api.map_ingest TO web_anon;
            """,
            raise_errors=True,
        )

        for old, new in renamed.items():
            for kind in STAGING_KINDS:
                source, target = f"{old}_{kind}", f"{table_prefix(new)}_{kind}"
                if source == target or source not in tables:
                    continue
                if target in tables:
                    raise MacrostratError(
                        f"Cannot rename sources.{source}: sources.{target} already exists"
                    )
                db.run_sql(
                    "ALTER TABLE {source} RENAME TO {target}",
                    dict(
                        source=Identifier("sources", source), target=Identifier(target)
                    ),
                    raise_errors=True,
                )
                tables.add(target)

        # A primary table that followed the old slug follows the new one.
        updates = [
            dict(old=old, new=new, prefix=table_prefix(new))
            for old, new in renamed.items()
            if old != new or table_prefix(new) != new
        ]
        if updates:
            db.run_query(
                """
                UPDATE maps.sources SET
                  slug = :new,
                  primary_table = CASE WHEN primary_table = :old || '_polygons'
                    THEN :prefix || '_polygons' ELSE primary_table END,
                  primary_line_table = CASE WHEN primary_line_table = :old || '_lines'
                    THEN :prefix || '_lines' ELSE primary_line_table END
                WHERE slug = :old
                """,
                updates,
            )
        db.session.commit()

        db.run_sql(
            f"ALTER TABLE maps.sources ADD CONSTRAINT {CONSTRAINT}"
            f" CHECK (slug ~ '{SLUG_PATTERN}')",
            raise_errors=True,
        )


def _refuse_collisions(rows, renamed: dict[str, str]):
    """Two slugs that normalize alike are duplicates to resolve by hand."""
    ids = {r.slug: r.source_id for r in rows}
    by_new = defaultdict(list)
    for old, new in renamed.items():
        by_new[new].append(old)
    clashes = {new: olds for new, olds in by_new.items() if len(olds) > 1}
    empty = [old for old, new in renamed.items() if new == ""]
    if not clashes and not empty:
        return
    lines = [
        f"  {' / '.join(f'{old} ({ids[old]})' for old in sorted(olds))} -> {new}"
        for new, olds in sorted(clashes.items())
    ]
    lines += [f"  {old!r} ({ids[old]}) has no letters or digits" for old in empty]
    raise MacrostratError(
        "Map slugs would collide in kebab-case",
        details="Resolve these before migrating (source ids in parentheses):\n"
        + "\n".join(lines),
    )
