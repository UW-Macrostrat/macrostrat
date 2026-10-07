from collections import defaultdict

from sqlalchemy import text

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database
from macrostrat.map_utils.slugs import (
    SLUG_PATTERN,
    STAGING_KINDS,
    slugify,
    table_prefix,
)
from macrostrat.schema_management import Migration, _not, has_columns

CONSTRAINT = "sources_slug_kebab"


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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
        # The session's reads lock maps.sources, which the ALTERs below would wait on.
        db.session.commit()
        with db.engine.begin() as conn:
            slugs = conn.execute(text("SELECT slug FROM maps.sources")).scalars()
            renamed = {slug: slugify(slug) for slug in slugs}
            _refuse_collisions(renamed)

            tables = set(
                conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables"
                        " WHERE table_schema = 'sources'"
                    )
                ).scalars()
            )

            conn.execute(
                text(
                    "ALTER TABLE maps_metadata.ingest_process DROP COLUMN IF EXISTS slug CASCADE"
                )
            )
            conn.execute(
                text(
                    "CREATE OR REPLACE VIEW macrostrat_api.map_ingest AS"
                    " SELECT * FROM maps_metadata.ingest_process"
                )
            )
            conn.execute(
                text(
                    "GRANT SELECT, UPDATE ON macrostrat_api.map_ingest TO web_user, web_admin"
                )
            )
            conn.execute(text("GRANT SELECT ON macrostrat_api.map_ingest TO web_anon"))

            for old, new in renamed.items():
                for kind in STAGING_KINDS:
                    source, target = f"{old}_{kind}", f"{table_prefix(new)}_{kind}"
                    if source == target or source not in tables:
                        continue
                    if target in tables:
                        raise MacrostratError(
                            f"Cannot rename sources.{source}: sources.{target} already exists"
                        )
                    conn.execute(
                        text(f"ALTER TABLE sources.{_q(source)} RENAME TO {_q(target)}")
                    )
                    tables.add(target)

            # A primary table that followed the old slug follows the new one.
            for old, new in renamed.items():
                conn.execute(
                    text(
                        """
                        UPDATE maps.sources SET
                          slug = :new,
                          primary_table = CASE WHEN primary_table = :old || '_polygons'
                            THEN :prefix || '_polygons' ELSE primary_table END,
                          primary_line_table = CASE WHEN primary_line_table = :old || '_lines'
                            THEN :prefix || '_lines' ELSE primary_line_table END
                        WHERE slug = :old
                        """
                    ),
                    dict(old=old, new=new, prefix=table_prefix(new)),
                )

            conn.execute(
                text(
                    f"ALTER TABLE maps.sources ADD CONSTRAINT {CONSTRAINT}"
                    f" CHECK (slug ~ '{SLUG_PATTERN}')"
                )
            )


def _refuse_collisions(renamed: dict[str, str]):
    """Two slugs that normalize alike are duplicates to resolve by hand."""
    by_new = defaultdict(list)
    for old, new in renamed.items():
        by_new[new].append(old)
    clashes = {new: olds for new, olds in by_new.items() if len(olds) > 1}
    empty = [old for old, new in renamed.items() if new == ""]
    if not clashes and not empty:
        return
    lines = [
        f"  {' / '.join(sorted(olds))} -> {new}"
        for new, olds in sorted(clashes.items())
    ]
    lines += [f"  {old!r} has no letters or digits" for old in empty]
    raise MacrostratError(
        "Map slugs would collide in kebab-case",
        details="Resolve these before migrating:\n" + "\n".join(lines),
    )
