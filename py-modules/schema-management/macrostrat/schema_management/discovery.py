"""Convention-driven discovery of schema subsystems from the filesystem.

A subsystem is declared in SQL with a lightweight frontmatter header, so the
chunk graph is *derived* from the files rather than hand-listed in Python. Two
shapes are recognized:

- a standalone ``.sql`` file whose header carries frontmatter → a single-file
  subsystem (the file is its content);
- a directory containing an ``_index.sql`` → a subsystem. ``_index.sql`` is the
  *lead file*: its header carries the frontmatter, and its SQL body is applied
  **first** (so it can do setup the rest of the directory relies on), followed by
  the directory's other ``.sql`` files in filename order.

Frontmatter is a block of ``-- @key: value`` comment lines in the file header::

    -- @subsystem: maps
    -- @depends-on: macrostrat

``@subsystem`` overrides the name (default: file stem / directory name);
``@depends-on`` is a comma/space separated list of other subsystems.

Note: **environment is assigned externally** by the loader (via ``discover_chunks``'s
``environments`` argument, chosen by *where* the chunks are loaded from) — SQL does
not declare the environments it runs in. A stray ``@environments`` in frontmatter is
ignored with a warning.
"""

import re
from pathlib import Path

from macrostrat.core import SchemaDefinition
from macrostrat.core.schema_definition import sql_files
from macrostrat.utils import get_logger

log = get_logger(__name__)

INDEX_FILE = "_index.sql"

_FRONTMATTER_RE = re.compile(r"^\s*--\s*@([\w-]+)\s*:\s*(.*?)\s*$")
# Frontmatter keys that mark a standalone file as its own subsystem.
_SUBSYSTEM_KEYS = {"subsystem", "depends-on"}


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse ``-- @key: value`` lines from a file's leading comment header.

    Scanning stops at the first line of actual SQL, so only header frontmatter is
    considered (a stray ``@key:`` deeper in the file is ignored).
    """
    meta: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = _FRONTMATTER_RE.match(line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
            continue
        # Tolerate other header comments (doc blocks, plain `--` notes).
        if stripped.startswith(("--", "/*", "*")):
            continue
        break  # first real SQL statement — header is over
    return meta


def _split_list(value: str) -> list[str]:
    return [item for item in re.split(r"[,\s]+", value.strip()) if item]


def _chunk_from(
    meta: dict, name_default: str, provides: list[Path], environments, owner
) -> SchemaDefinition:
    name = meta.get("subsystem", name_default)
    if "environments" in meta:
        log.warning(
            "Ignoring @environments in frontmatter for subsystem %r — environment is "
            "assigned externally by load location, not declared in SQL.",
            name,
        )
    return SchemaDefinition(
        name=name,
        depends_on=_split_list(meta.get("depends-on", "")),
        provides=provides,
        environments=environments,
        owner=owner,
    )


def discover_chunks(
    root: Path, *, environments=None, owner=None
) -> list[SchemaDefinition]:
    """Build ``SchemaDefinition``s for every subsystem found directly under ``root``.

    ``environments`` (a frozenset, or ``None`` for "all environments") and ``owner``
    (the applying role, or ``None`` for the connector) are applied to every subsystem
    discovered here — the caller chooses both by *where* it is loading from, rather
    than the SQL declaring them (ownership is a property of who applies a chunk, not
    of the file).

    Entries that aren't subsystems (a directory with no ``_index.sql``, a loose
    ``.sql`` with no frontmatter) are skipped — during migration they remain part
    of whatever explicit/default chunk still owns them.
    """
    chunks: list[SchemaDefinition] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            index = entry / INDEX_FILE
            if not index.exists():
                continue
            meta = parse_frontmatter(index.read_text())
            # _index.sql is the lead file: applied first, then the rest in
            # filename order. Its frontmatter header is just comments to the DB.
            others = [f for f in sql_files(entry) if f.name != INDEX_FILE]
            chunks.append(
                _chunk_from(meta, entry.name, [index, *others], environments, owner)
            )
        elif entry.suffix == ".sql" and entry.name != INDEX_FILE:
            meta = parse_frontmatter(entry.read_text())
            if _SUBSYSTEM_KEYS & meta.keys():
                chunks.append(
                    _chunk_from(meta, entry.stem, [entry], environments, owner)
                )
    return chunks
