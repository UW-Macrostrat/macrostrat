"""Map source slugs, and the names derived from them.

A slug is kebab-case: lowercase letters and digits joined by single hyphens.
Postgres identifiers want underscores, so every name built from a slug -- the
`sources.<prefix>_polygons` staging tables, `maps.sources.primary_table` --
takes its prefix from `table_prefix()` rather than from the slug itself.
"""

import re

SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
STAGING_KINDS = ("polygons", "lines", "points")

_SLUG = re.compile(SLUG_PATTERN)
_SEPARATORS = re.compile(r"[^a-z0-9]+")


class InvalidSlug(ValueError):
    pass


def slugify(text: str) -> str:
    """The kebab-case form of any name: runs of other characters become one hyphen."""
    return _SEPARATORS.sub("-", text.lower()).strip("-")


def check_slug(slug: str) -> str:
    """Return `slug` unchanged, or refuse it with the form it should take."""
    if _SLUG.match(slug):
        return slug
    raise InvalidSlug(
        f"Map slug {slug!r} is not kebab-case; use {slugify(slug)!r} "
        "(lowercase letters and digits joined by single hyphens)"
    )


def is_slug(slug: str) -> bool:
    return _SLUG.match(slug) is not None


def selector(value: str) -> str:
    """A slug or glob as typed, with underscores read as hyphens.

    Slugs used underscores until 2026; this keeps old names and globs
    (`japan_*`) resolving.
    """
    return value.replace("_", "-")


def table_prefix(slug: str) -> str:
    """The identifier prefix for a slug's tables: `az-littlehorn-100k` -> `az_littlehorn_100k`."""
    return slug.replace("-", "_")


def staging_table(slug: str, kind: str) -> str:
    """The unqualified staging table name, in the `sources` schema."""
    if kind not in STAGING_KINDS:
        raise ValueError(f"Unknown staging table kind {kind!r}")
    return f"{table_prefix(slug)}_{kind}"
