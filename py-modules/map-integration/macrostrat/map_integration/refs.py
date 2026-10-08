"""Map references: rows in `macrostrat.refs` and the links that attach them.

A reference is linked at the highest level it holds throughout -- the map, a
legend entry, a polygon, a line -- and a feature's references are the union of
every level (see `maps.ref_type`). A pipeline resolves its citations to
reference ids with `resolve_refs`, then replaces the links it owns with
`write_links`.

`macrostrat.refs` is shared with columns and has no unique constraint, so a
citation is matched against what is there -- by DOI, else by authors, year and
title, ignoring punctuation and what follows the title's colon -- and a reference
is never deleted.
"""

import re
from dataclasses import dataclass
from typing import Iterable, Optional

#: Feature level: (link table, key column).
LEVELS = {
    "map": ("maps.map_refs", "source_id"),
    "legend": ("maps.legend_refs", "legend_id"),
    "polygon": ("maps.polygon_refs", "map_id"),
    "line": ("maps.line_refs", "line_id"),
}

# "Hintze, L.F., and Brown, K.D., 2000, Digital Geologic Map of Utah: ...", the
# year sometimes followed by an edition, "1995 (latest update 2011)", sometimes
# uncertain, "[1952?]", and sometimes set off by periods: "Fisher, D.W. 1977. ...".
_CITATION = re.compile(
    r"^(?P<author>.+?)[,.]\s*\[?(?P<year>(?:1[6-9]|20)\d\d)[a-z]?\??\]?"
    r"(?:\s*\([^)]*\))?\s*[,.:]\s*(?P<ref>.+)$",
    re.S,
)
_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)


@dataclass(frozen=True)
class Reference:
    author: str
    pub_year: int
    ref: str
    doi: Optional[str] = None
    url: Optional[str] = None


def parse_citation(
    text: str, *, doi: Optional[str] = None, url: Optional[str] = None
) -> Optional[Reference]:
    """Split an "Authors, year, title" citation; None when it has no year."""
    match = _CITATION.match(" ".join((text or "").split()))
    if match is None:
        return None
    return Reference(
        author=match["author"].strip(),
        pub_year=int(match["year"]),
        ref=match["ref"].strip(),
        doi=normalize_doi(doi),
        url=url or None,
    )


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi or not doi.strip():
        return None
    return _DOI_PREFIX.sub("", doi.strip()).lower() or None


_CONNECTIVES = re.compile(r"\b(?:and|others|et al)\b|&")
_NOT_WORD = re.compile(r"\W+")


def _text_key(author: str, pub_year: int, ref: str) -> tuple:
    """Authors, year and title: the title is the text before the first colon, so
    "Title: Publisher, 3 sheets" and "Title: Publisher" are one publication."""
    names = _NOT_WORD.sub("", _CONNECTIVES.sub(" ", (author or "").casefold()))
    title = _NOT_WORD.sub("", (ref or "").split(":", 1)[0].casefold())
    return (names, pub_year, title)


def reference_key(ref: Reference) -> tuple:
    """What two spellings of one publication share; see `_text_key`."""
    return _text_key(ref.author, ref.pub_year, ref.ref)


def same_reference(a: Reference, b: Reference) -> bool:
    """Whether two references name one publication, as `resolve_refs` matches them."""
    doi_a, doi_b = normalize_doi(a.doi), normalize_doi(b.doi)
    if doi_a and doi_b:
        return doi_a == doi_b
    return _text_key(a.author, a.pub_year, a.ref) == _text_key(
        b.author, b.pub_year, b.ref
    )


def resolve_refs(db, refs: Iterable[Reference]) -> dict[Reference, int]:
    """The `macrostrat.refs` id of each reference, inserting the missing ones."""
    refs = list(dict.fromkeys(refs))
    by_doi, by_text = {}, {}
    # Small enough to match in Python: a few thousand rows.
    for row in db.run_query(
        "SELECT id, author, pub_year, ref, doi FROM macrostrat.refs ORDER BY id"
    ):
        doi = normalize_doi(row.doi)
        if doi is not None:
            by_doi.setdefault(doi, row.id)
        by_text.setdefault(_text_key(row.author, row.pub_year, row.ref), row.id)

    ids = {}
    for ref in refs:
        key = _text_key(ref.author, ref.pub_year, ref.ref)
        doi = normalize_doi(ref.doi)
        ref_id = by_doi.get(doi) if doi else None
        if ref_id is None:
            ref_id = by_text.get(key)
        if ref_id is None:
            ref_id = db.run_query(
                """
                INSERT INTO macrostrat.refs
                  (pub_year, author, ref, doi, url, compilation_code)
                VALUES (:pub_year, :author, :ref, :doi, :url, '')
                RETURNING id
                """,
                dict(
                    pub_year=ref.pub_year,
                    author=ref.author,
                    ref=ref.ref,
                    doi=doi,
                    url=ref.url,
                ),
            ).scalar()
            if doi:
                by_doi[doi] = ref_id
            by_text[key] = ref_id
        ids[ref] = ref_id
    return ids


def place_links(
    features: Iterable[tuple], ref_type: str, *, feature_level: str = "polygon"
) -> dict[str, list[tuple]]:
    """Each reference at the highest level it holds throughout.

    `features` are `(source_id, legend_id, feature_id, ref)`, one per feature;
    `ref` is anything hashable -- a `Reference` before resolving, an id after --
    or None where the feature has none. A map whose features share one reference
    gets one map link; failing that, a legend entry whose features share one gets
    a legend link; failing that, each feature its own. A None keeps its group
    from being uniform and is never written. Returns `{level: [(key, ref,
    ref_type)]}`.
    """
    by_map: dict[int, list[tuple]] = {}
    for feature in features:
        by_map.setdefault(feature[0], []).append(feature)

    placed = {"map": [], "legend": [], feature_level: []}
    for source_id, rows in by_map.items():
        refs = {r[3] for r in rows}
        if len(refs) == 1 and None not in refs:
            placed["map"].append((source_id, refs.pop(), ref_type))
            continue
        by_legend: dict[Optional[int], list[tuple]] = {}
        for r in rows:
            by_legend.setdefault(r[1], []).append(r)
        for legend_id, group in by_legend.items():
            refs = {r[3] for r in group}
            if legend_id is not None and len(refs) == 1 and None not in refs:
                placed["legend"].append((legend_id, refs.pop(), ref_type))
            else:
                placed[feature_level].extend(
                    (r[2], r[3], ref_type) for r in group if r[3] is not None
                )
    return placed


def write_links(
    db,
    level: str,
    links: Iterable[tuple[int, int, str]],
    *,
    keys: Iterable[int],
    ref_types: Iterable[str],
) -> tuple[int, int]:
    """Replace the `ref_types` links of the `keys` features with `links`.

    `links` are `(feature key, ref_id, ref_type)`. Links of other types, or on
    other features, are left alone, so pipelines sharing a feature do not
    clobber each other. Returns (removed, written); the caller commits.
    """
    table, key_column = LEVELS[level]
    links = list(dict.fromkeys(links))
    removed = db.run_query(
        f"""
        DELETE FROM {table}
        WHERE {key_column} = ANY(CAST(:keys AS integer[]))
          AND ref_type = ANY(CAST(:ref_types AS text[]))
        """,
        dict(keys=list(keys), ref_types=list(ref_types)),
    ).rowcount
    written = 0
    if links:
        written = db.run_query(
            f"""
            INSERT INTO {table} ({key_column}, ref_id, ref_type)
            SELECT * FROM unnest(
              CAST(:keys AS integer[]),
              CAST(:ref_ids AS integer[]),
              CAST(:ref_types AS text[])
            )
            ON CONFLICT DO NOTHING
            """,
            dict(
                keys=[k for k, _, _ in links],
                ref_ids=[r for _, r, _ in links],
                ref_types=[t for _, _, t in links],
            ),
        ).rowcount
    return removed, written
