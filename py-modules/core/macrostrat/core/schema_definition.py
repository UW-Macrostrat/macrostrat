"""
A chunk of a declarative schema.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union

from macrostrat.database import Database

# A provider that applies its own statements to the database.
DBCallable = Callable[[Database], None]

# A declarative provider: a directory of .sql files, or a callable.
Provider = Union[Path, DBCallable]


@dataclass
class SchemaDefinition:
    """A named, dependency-ordered unit of declarative schema.

    Providers are applied in listed order once the chunk's ``depends_on`` are
    satisfied. A ``Path`` provider is treated as a directory of ``.sql`` files;
    any other callable receives the :class:`Database` and applies its own
    statements.
    """

    name: str
    depends_on: list[str] = field(default_factory=list)
    provides: list[Provider] = field(default_factory=list)
    # Environments in which this chunk applies. ``None`` means all environments.
    environments: Optional[frozenset[str]] = None
    database: str = "macrostrat"

    def applies_to(self, env: str) -> bool:
        return self.environments is None or env in self.environments

    def apply(self, db: Database) -> None:
        for provider in self.provides:
            if isinstance(provider, Path):
                apply_sql_dir(db, provider)
            elif callable(provider):
                provider(db)
            else:
                raise TypeError(
                    f"Chunk {self.name!r} provider must be a Path or callable, "
                    f"got {provider!r}"
                )


def apply_sql_dir(db: Database, directory: Path) -> None:
    """Apply every ``.sql`` file under ``directory`` in filename order.

    Mirrors the globbing in :func:`apply_schema_for_environment` exactly: recurse,
    sort by path, drop ``*.plan.sql``. Duplicated (rather than shared) to keep the
    composer additive; the parity test guards against drift.
    """
    if not directory.exists():
        return
    fixtures = sorted(directory.rglob("*.sql"))
    fixtures = [f for f in fixtures if not f.name.endswith(".plan.sql")]
    if not fixtures:
        return
    db.run_fixtures(fixtures)
