"""Collection of Macrostrat's schema chunks.

The single, readable answer to "what is the database schema made of?" — a mix of:

- **discovered** subsystems, found on the filesystem by their frontmatter
  (`discover_chunks`); the first real migration to this convention is ``maps``
  (``schema/maps/`` with an ``_index.sql`` lead file); and
- **explicit** chunks for the parts of ``schema/core`` not yet split out, plus
  the function-backed ``TopologySchema``.

Because the build still relies on filename order, the un-migrated ``core``
remainder is temporarily bracketed *around* the extracted ``maps`` subsystem:
``macrostrat`` = everything before maps (the core relational model + auth),
``core`` = everything after. These two buckets shrink as more subsystems are
pulled out; the dependency chain preserves today's exact application order.
"""

from pathlib import Path

from macrostrat.core.config import settings
from macrostrat.map_topology.config import TopologySchema

from .composer import SchemaDefinition
from .discovery import discover_chunks

# Environments (defs.py vocabulary) in which the dev-only layers apply.
_DEV_ENVS = frozenset({"development", "local"})

# Foundational files (roles, globals, public schema), applied before everything.
# This is the one chunk that runs as the connector (superuser): it creates roles,
# extensions, and the shared ``public`` schema — DDL an application role can't do —
# so its ``owner`` stays ``None`` and its object ownership stays explicit in the SQL.
_PUBLIC_FILES = ["0000-globals.sql", "0000-roles.sql", "0001-public.sql"]

# Global/cross-owner grants (on ``public``/``topology``/``sources``/the database)
# that only a superuser can issue. Kept out of the application chunks and applied
# last as its own ``owner=None`` chunk, so the app chunks stay purely structural
# and can run as ``macrostrat``. See the 2026-07-17 design note in the feature doc.
_PERMISSIONS_FILE = "9500-permissions.sql"

# Temporary split point: ``maps`` was extracted to ``schema/maps/``. Core entries
# sorting before this name form the "before maps" bucket (``macrostrat``); those
# after form the "after maps" bucket (``core``).
_MAPS_BOUNDARY = "0002-maps"

# Application chunks are applied as this role (create-as-owner), so their objects
# are born owned by it and the SQL carries no ``ALTER … OWNER TO`` boilerplate.
_APP_OWNER = "macrostrat"


def _core_dir() -> Path:
    return settings.srcroot / "schema" / "core"


def all_chunks() -> list[SchemaDefinition]:
    """Every schema chunk, independent of environment."""
    schema_dir = settings.srcroot / "schema"
    core = _core_dir()
    public = set(_PUBLIC_FILES)

    entries = sorted(core.iterdir())
    before_maps = [
        p for p in entries if p.name not in public and p.name < _MAPS_BOUNDARY
    ]
    # `after_maps` is the `core` remainder minus the permissions file, which becomes
    # its own superuser-owned chunk applied last.
    after_maps = [
        p for p in entries if p.name > _MAPS_BOUNDARY and p.name != _PERMISSIONS_FILE
    ]

    return [
        SchemaDefinition(name="public", provides=[core / f for f in _PUBLIC_FILES]),
        # "before maps" — the core relational model + auth.
        SchemaDefinition(
            name="macrostrat",
            depends_on=["public"],
            provides=before_maps,
            owner=_APP_OWNER,
        ),
        # `maps` is discovered from schema/maps/ (depends_on macrostrat via frontmatter).
        *discover_chunks(schema_dir, owner=_APP_OWNER),
        # "after maps" — storage, metadata, tiles, … (still flat).
        SchemaDefinition(
            name="core", depends_on=["maps"], provides=after_maps, owner=_APP_OWNER
        ),
        # Global/cross-owner grants, applied last as the connector (superuser).
        SchemaDefinition(
            name="permissions",
            depends_on=["core"],
            provides=[core / _PERMISSIONS_FILE],
        ),
        SchemaDefinition(
            name="development",
            depends_on=["permissions"],
            provides=[schema_dir / "development"],
            environments=_DEV_ENVS,
            owner=_APP_OWNER,
        ),
        # PostgREST API layer (macrostrat_api schema): views over the core relational
        # model plus a few API functions. Consolidated from the old
        # `development/9000-macrostrat_api.sql` pg_dump and the `column_builder` migration
        # (which supplied the clean core views/functions in 01/02). Depends on
        # `development` because some views read `macrostrat_kg`; dev-only for the same
        # reason.
        SchemaDefinition(
            name="macrostrat_api",
            depends_on=["development"],
            provides=[schema_dir / "macrostrat_api"],
            environments=_DEV_ENVS,
            owner=_APP_OWNER,
        ),
        SchemaDefinition(
            name="local",
            depends_on=["development"],
            provides=[schema_dir / "local"],
            environments=frozenset({"local"}),
            owner=_APP_OWNER,
        ),
        TopologySchema,
    ]


def chunks_for_environment(env: str) -> list[SchemaDefinition]:
    """The chunks that apply in the given environment."""
    return [c for c in all_chunks() if c.applies_to(env)]
