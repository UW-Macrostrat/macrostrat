"""Freeze legacy carto's prioritization into the compilations model."""

from macrostrat.database import Database
from macrostrat.schema_management import Migration, exists, has_columns

from ..carto_v1 import UMBRELLA, write


def _slug_exists(slug: str):
    def check(db: Database) -> bool:
        return bool(
            db.run_query(
                "SELECT count(*) FROM maps.sources WHERE slug = :slug",
                dict(slug=slug),
            ).scalar()
        )

    return check


def _has_legacy_carto(db: Database) -> bool:
    """Whether there is a v1 prioritization here to extract.

    Not "does the table exist" -- a schema built fresh under authored membership
    has `carto.polygons` and nothing in it, and there is nothing to freeze. This
    is also what keeps the migration inert on a new database, where generating
    seven empty compilations would be noise and where auto-authoring membership
    is the behaviour that was deliberately retired.
    """
    return bool(db.run_query("SELECT EXISTS (SELECT 1 FROM carto.polygons)").scalar())


class CartoV1Compilation(Migration):
    """Read legacy carto's curation out of `maps.sources.display_scales`.

    Writes it down as compilations: `tiny-v1` .. `large-v1`, the three
    `carto-*-v1` composites, and a `carto-v1` umbrella naming the snapshot.

    Time-limited, which is why it is a migration rather than an operator's
    choice. The extraction is only possible while `display_scales` and the
    `carto` tables still exist, and both are transitional; a database upgraded
    after they go away could never recover the v1 ranking. It is also the last
    step before `maps.sources.new_priority` can be retired -- v1's ordering is
    the one thing that column still expresses which per-compilation priority
    does not.

    The snapshot is not served: it gets no `map_layer` rows, so
    `sync-priority-paths` never projects its composition into the topology and
    nothing materializes faces for it. It exists to be inspected, diffed against
    `carto`, and curated.
    """

    name = "carto-v1-compilation"
    subsystem = "maps"

    depends_on = []
    readiness_state = "ga"

    # The work is Python, not SQL files beside this module.
    load_sql_files = False
    fixtures = [write]

    # Creates `maps.sources` rows and membership edges, but removes nothing and
    # rewrites no map.
    destructive = False

    preconditions = [
        exists("map_bounds", "compilation_member", "map_area"),
        exists("carto", "polygons"),
        has_columns("maps", "sources", "slug", "display_scales", "new_priority"),
        _has_legacy_carto,
    ]

    # Existence of the umbrella, not its contents. The snapshot is handed over to
    # be curated -- members will be added, removed and re-ranked -- so any
    # postcondition describing the membership would either fight that curation or
    # quietly re-impose the generated answer over it.
    postconditions = [
        _slug_exists(UMBRELLA + "-v1"),
        _slug_exists(UMBRELLA + "-v1-small"),
    ]
