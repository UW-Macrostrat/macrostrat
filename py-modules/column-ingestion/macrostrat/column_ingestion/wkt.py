"""A syntax check of the geometry text a workbook gives in `geom` and `rgeom`.

PostGIS is what reads the geometry, but only when the column is written, and its
parse errors name neither the cell nor the problem. This check runs while the sheet
is parsed, so a bad cell becomes a notice the dry run can show. It covers what makes
PostGIS refuse the text outright — syntax, the kind of geometry, unclosed rings,
coordinates a geography cannot hold. Validity (a self-intersecting polygon) is still
judged by PostGIS, in `column_utils.resolve_geometry`.
"""

from __future__ import annotations

import re

from . import notices

#: The kinds of geometry a column's `geom` may be: an area, or a measured traverse.
ACCEPTED_TYPES = {"POLYGON", "MULTIPOLYGON", "LINESTRING", "MULTILINESTRING"}

#: How deeply each type nests its coordinate lists.
_DEPTHS = {
    "POINT": {1},
    "LINESTRING": {1},
    # Points in a MULTIPOINT may be bracketed or not
    "MULTIPOINT": {1, 2},
    "POLYGON": {2},
    "MULTILINESTRING": {2},
    "MULTIPOLYGON": {3},
}

_EXAMPLE = "e.g. `POLYGON ((lng lat, lng lat, ...))` or `LINESTRING (lng lat, ...)`"

_NUMBER = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_TOKEN = re.compile(rf"\s*(?:({_NUMBER})|([A-Za-z]+)|([(),]))")
_PAIR = re.compile(rf"^\s*\(?\s*({_NUMBER})\s*[,;\s]\s*({_NUMBER})\s*\)?\s*$")
# A hemisphere letter after a number, but not an exponent (`1E-5`)
_DEGREES = re.compile(r"[°º˚'′\"″]|\d\s*[NSEW](?![\w.+-])")


class WKTProblem(ValueError):
    pass


def check_wkt(text: str, column: str = "geom") -> str | None:
    """What stops `text` being read as a column geometry, or `None` if nothing does."""
    if _PAIR.match(text):
        return (
            f"{text!r} looks like a latitude, longitude pair: put a point in the "
            "`lat` and `lng` columns instead"
        )
    if _DEGREES.search(text):
        return (
            f"{text!r} looks like degrees and minutes: give the location in decimal "
            "degrees in the `lat` and `lng` columns instead"
        )
    try:
        kind, coords = _parse(text)
    except WKTProblem as err:
        return f"{text!r} is not WKT geometry ({err}); {_EXAMPLE}"

    if kind == "POINT":
        return (
            f"a point goes in the `lat` and `lng` columns; `{column}` takes a polygon "
            "or a line"
        )
    if kind not in ACCEPTED_TYPES:
        return f"`{column}` takes a polygon or a line, not a {kind}; {_EXAMPLE}"
    if coords is None:
        return f"{text!r} is an empty geometry"

    lines = {
        "LINESTRING": [coords],
        "MULTILINESTRING": coords,
        "POLYGON": coords,
        "MULTIPOLYGON": [ring for polygon in coords for ring in polygon],
    }[kind]
    is_area = kind in ("POLYGON", "MULTIPOLYGON")
    for line in lines:
        if is_area and len(line) < 4:
            return "a polygon ring needs at least four points"
        if is_area and line[0][:2] != line[-1][:2]:
            return "a polygon ring must end on the point it starts from"
        if len(line) < 2:
            return "a line needs at least two points"
        for x, y, *_ in line:
            if abs(x) > 180 or abs(y) > 90:
                return (
                    f"the coordinate ({x:g} {y:g}) is not a longitude and latitude; "
                    "WKT gives longitude first, in decimal degrees"
                )
    return None


def parse_geometry(value, column: str, **where) -> str | None:
    """Geometry text as given, or `None` (with an error notice) where it is unusable.

    Outside a notice collector an unusable value raises instead.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    problem = check_wkt(text, column)
    if problem is None:
        return text
    notices.error_or_raise(
        ValueError(f"`{column}`: {problem}"),
        "invalid-geometry",
        column=column,
        **where,
    )
    return None


def _parse(text: str):
    tokens = _tokenize(text)
    kind = tokens.pop(0) if tokens and tokens[0].isalpha() else None
    if kind is None:
        raise WKTProblem("it should start with a geometry type")
    kind = kind.upper()
    if kind not in _DEPTHS:
        raise WKTProblem(f"{kind} is not a geometry type")
    if tokens and tokens[0].upper() in ("Z", "M", "ZM"):
        tokens.pop(0)
    if tokens and tokens[0].upper() == "EMPTY" and len(tokens) == 1:
        return kind, None
    coords, depth = _list(tokens)
    if tokens:
        raise WKTProblem(f"unexpected {tokens[0]!r} after the geometry")
    if depth not in _DEPTHS[kind]:
        raise WKTProblem(f"the brackets do not nest as a {kind}'s do")
    if kind == "POINT" and len(coords) != 1:
        raise WKTProblem("a POINT has one coordinate")
    return kind, coords


def _tokenize(text: str) -> list[str]:
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if match is None or match.end() == pos:
            raise WKTProblem(f"unexpected {text[pos:].strip()[:10]!r}")
        tokens.append(next(group for group in match.groups() if group is not None))
        pos = match.end()
    return tokens


def _list(tokens: list[str]) -> tuple[list, int]:
    """A bracketed list of coordinates or of lists, and how deeply it nests."""
    if not tokens or tokens.pop(0) != "(":
        raise WKTProblem("expected `(`")
    items, depths = [], set()
    while True:
        if tokens and tokens[0] == "(":
            item, depth = _list(tokens)
            depths.add(depth + 1)
        else:
            item = _coordinate(tokens)
            depths.add(1)
        items.append(item)
        if not tokens:
            raise WKTProblem("a bracket is not closed")
        separator = tokens.pop(0)
        if separator == ")":
            break
        if separator != ",":
            raise WKTProblem(f"unexpected {separator!r}")
    if len(depths) > 1:
        raise WKTProblem("brackets are unbalanced")
    return items, depths.pop()


def _coordinate(tokens: list[str]) -> tuple[float, ...]:
    numbers = []
    while tokens and tokens[0] not in ("(", ")", ","):
        token = tokens.pop(0)
        try:
            numbers.append(float(token))
        except ValueError:
            raise WKTProblem(f"{token!r} is not a number")
    if len(numbers) < 2:
        raise WKTProblem(
            "each point needs a longitude and a latitude separated by a space, "
            "and points are separated by commas"
        )
    if len(numbers) > 4:
        raise WKTProblem("a point has at most four numbers; are commas missing?")
    return tuple(numbers)
