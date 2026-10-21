"""Restrict a schema sweep to named database objects.

``macrostrat schema sync --object`` takes patterns naming a schema (``maps``) or a
schema-qualified object (``maps.legend_lookup``), with shell-style globs in either
part. Each sweep names the objects its statements touch; a statement is kept when
any of them matches. Matching is case-insensitive, as unquoted identifiers are.
"""

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Iterable, NamedTuple, Optional


class ObjectName(NamedTuple):
    schema: str
    # None for a statement on the schema as a whole (``GRANT … ON SCHEMA``).
    name: Optional[str] = None


def _normalize(identifier: str) -> str:
    return identifier.replace('"', "").strip().lower()


def parse_object_name(identifier: str) -> ObjectName:
    """``"Maps".foo(integer)`` → ``ObjectName("maps", "foo")``; unqualified is ``public``."""
    schema, _, name = _normalize(identifier.split("(", 1)[0]).rpartition(".")
    return ObjectName(schema or "public", name)


def schema_names(identifiers: str) -> list[ObjectName]:
    """A comma-separated list of schemas, as named in ``ON SCHEMA a, b``."""
    return [ObjectName(_normalize(s)) for s in identifiers.split(",")]


@dataclass(frozen=True)
class ObjectSelector:
    patterns: tuple[ObjectName, ...]

    @classmethod
    def parse(cls, patterns: Iterable[str]) -> "ObjectSelector":
        parsed = []
        for pattern in patterns:
            schema, _, name = _normalize(pattern).partition(".")
            parsed.append(ObjectName(schema, name or None))
        return cls(tuple(parsed))

    def matches(self, objects: Iterable[ObjectName]) -> bool:
        return any(_match(p, o) for o in objects for p in self.patterns)


def _match(pattern: ObjectName, obj: ObjectName) -> bool:
    if not fnmatchcase(obj.schema, pattern.schema):
        return False
    if pattern.name is None:
        return True
    # A schema-wide statement (``ALL TABLES IN SCHEMA``) is not one object's.
    return obj.name is not None and fnmatchcase(obj.name, pattern.name)
