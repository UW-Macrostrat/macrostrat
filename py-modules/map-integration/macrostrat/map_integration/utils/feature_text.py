"""Whether a staged feature's value says what the feature is.

Shared by `normalize review-points`, `normalize preflight`, `normalize
review-layers` and the GeMS ingest's line typing. A value says something when
it is not blank, an id, a symbol code, a GUID or an editing record.
"""

import re
from typing import Optional

#: Values that are no value.
BLANK = {"", "none", "null", "<null>", "unnamed", "not assigned", "n/a", "nan", "-"}

GUID = re.compile(r"\{?[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\}?", re.I)

#: A single word that is a code: a number, a symbol code ("1.1.1", "AC",
#: "DI30"), a project name ("rpNarrowsDGM").
CODE = re.compile(r"[\d.\s-]+|[A-Z]{1,5}\d*|\S*[a-z]+[A-Z]\S*|\S*\d\S*")

#: Where a feature came from, not what it is: "import from CAF ...", "AZGS 2005
#: Fairbanks quad", "shipman digitize 2005", a GPS waypoint, a shapefile.
PROVENANCE = re.compile(
    r"^import from|displayname:|outcropboundarytrace|datasource|"
    r"\bjoin on\b|deprecate|\bdigiti[sz]|\b(?:19|20)\d\d\b|field\s?mapping|"
    r"\bquad(?:rangle)?\b|\bsur?ficial map\b|\bcompil|waypoint|\.shp\b|statemap",
    re.I,
)

#: Words that do not change what a value says, for comparing values.
STOPWORDS = {"located", "location", "placed", "is", "on", "the", "of", "a", "and"}


def pertinent(value) -> Optional[str]:
    """`value` with its whitespace collapsed, if it says something about the
    feature; else None."""
    if value is None or isinstance(value, (bool, int, float)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if (
        text.lower().strip(" .") in BLANK
        or GUID.fullmatch(text)
        or PROVENANCE.search(text)
    ):
        return None
    if " " not in text and CODE.fullmatch(text):
        return None
    return text


def first(feature: dict, columns: list[str]) -> Optional[str]:
    """The first of `columns` whose value is pertinent."""
    return next((v for c in columns if (v := pertinent(feature.get(c)))), None)


def words(text: Optional[str]) -> set[str]:
    """The words of `text`, for asking whether one value says more than
    another ("-ly" dropped: "approximately" is "approximate")."""
    found = set()
    for word in re.findall(r"[a-z]+", (text or "").lower()):
        if word.endswith("ly"):
            word = word[:-2]
        if word not in STOPWORDS:
            found.add(word)
    return found


def blank_sql(column: str):
    """SQL true where `column` holds no value as `BLANK` counts them, for
    counting over large tables in the database. Binds `:blank_values`:
    pass `blank_values=sorted(BLANK)` with the query."""
    from psycopg.sql import SQL, Identifier

    return SQL(
        "coalesce(lower(trim(both ' .' from CAST({column} AS text))), '')"
        " = ANY(CAST(:blank_values AS text[]))"
    ).format(column=Identifier(column))
