"""
A chunk of a declarative schema.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union

from macrostrat.database import Database

# A provider that applies its own statements to the database.
DBCallable = Callable[[Database], None]

# A declarative provider: a directory (or single file) of SQL, or a callable.
Provider = Union[Path, DBCallable]


@dataclass
class SchemaDefinition:
    """A named, dependency-ordered unit of declarative schema.

    Providers are applied in listed order once the chunk's ``depends_on`` are
    satisfied. A ``Path`` provider is a directory of ``.sql`` files (applied in
    filename order) or a single ``.sql`` file; a callable receives the
    :class:`Database` and applies its own statements.
    """

    name: str
    depends_on: list[str] = field(default_factory=list)
    provides: list[Provider] = field(default_factory=list)
    # Environments in which this chunk applies. ``None`` means all environments.
    environments: Optional[frozenset[str]] = None
    database: str = "macrostrat"
    # Role that applies this chunk (via session ``SET ROLE``), so the chunk's
    # objects are *born owned* by it — replacing per-object ``ALTER … OWNER TO``.
    # ``None`` applies the chunk as the connector (superuser) for foundational DDL
    # (extensions, roles, the ``public`` schema) that an application role can't do.
    owner: Optional[str] = None

    def applies_to(self, env: str) -> bool:
        return self.environments is None or env in self.environments

    def apply(
        self, db: Database, *, transform_statement=None, statement_filter=None
    ) -> None:
        """Apply this chunk's providers.

        ``transform_statement`` / ``statement_filter`` are forwarded to SQL file
        application (e.g. to skip index/grant statements in tests).
        """
        for provider in self.provides:
            if isinstance(provider, Path):
                apply_sql_path(
                    db,
                    provider,
                    transform_statement=transform_statement,
                    statement_filter=statement_filter,
                )
            elif callable(provider):
                # Function-backed providers apply their own statements.
                provider(db)
            else:
                raise TypeError(
                    f"Chunk {self.name!r} provider must be a Path or callable, "
                    f"got {provider!r}"
                )


def sql_files(path: Path) -> list[Path]:
    """The ``.sql`` files at ``path``, in filename order.

    ``path`` may be a directory (recursed, sorted by path) or a single ``.sql``
    file; ``*.plan.sql`` files are always skipped. A path that exists as neither
    yields no files. Shared by every ``Path`` provider so file discovery is
    defined in exactly one place.
    """
    if path.is_dir():
        files = sorted(path.rglob("*.sql"))
    elif path.is_file():
        files = [path]
    else:
        files = []
    return [f for f in files if not f.name.endswith(".plan.sql")]


def apply_sql_path(
    db: Database, path: Path, *, transform_statement=None, statement_filter=None
) -> None:
    """Apply the ``.sql`` file(s) at ``path`` in filename order (see :func:`sql_files`)."""
    fixtures = sql_files(path)
    if fixtures:
        db.run_fixtures(
            fixtures,
            transform_statement=transform_statement,
            statement_filter=statement_filter,
        )
