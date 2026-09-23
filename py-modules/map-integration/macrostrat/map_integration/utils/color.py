"""Normalize the colour encodings that arrive in `sources.*` staging tables.

`maps.legend.color` is consumed as an HTML hex colour -- `process/legend_lookup`
hands it straight to `spectra.html`, which accepts nothing else. Source data
rarely arrives that way: GeMS writes `areafillrgb`, and publishers fill it by
hand, so one ingest can carry `255,255,221`, `(255, 255, 77)` and
`rgb(255, 204, 230)` for colours drawn from the same palette.

Parsing is deliberately narrow. Anything not recognised returns `None` rather
than a guess, because a wrong colour is worse than an absent one: it renders,
so nobody goes looking.
"""

import re

__all__ = ["normalize_color"]

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
_SHORT_HEX = re.compile(r"^#([0-9a-fA-F]{3})$")
# `rgb(...)`, `(...)`, `{...}`, or a bare comma/semicolon/space-separated
# triple -- publishers bracket these every way. A trailing separator is
# tolerated: `255,235,169,` appears 272 times in NGS.
_TRIPLE = re.compile(
    r"^(?:rgba?\s*)?[(\[{]?\s*([0-9]{1,3})\s*[,;\s]\s*([0-9]{1,3})\s*[,;\s]\s*"
    r"([0-9]{1,3})\s*(?:[,;\s]\s*([0-9.]+)\s*)?[)\]}]?[,;\s]*$"
)
# Three zero-padded components run together: `249115087` is 249, 115, 87. Only
# ever nine digits, so it cannot be confused with a hex value.
_PACKED = re.compile(r"^([0-9]{3})([0-9]{3})([0-9]{3})$")


def normalize_color(value: str | None) -> str | None:
    """Return `value` as `#rrggbb`, or `None` if it is not a colour we recognise.

    Handles hex (passed through, lowercased), `r,g,b` in the several bracketings
    publishers use, and nine-digit packed triples. An alpha channel is dropped:
    `maps.legend.color` has nowhere to put one, and every alpha seen in practice
    is opaque.
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if match := _HEX.match(text):
        return "#" + match.group(1).lower()

    if match := _SHORT_HEX.match(text):
        # `#abc` means `#aabbcc`.
        return "#" + "".join(c * 2 for c in match.group(1).lower())

    match = _TRIPLE.match(text) or _PACKED.match(text)
    if match is None:
        return None

    # Leading zeros are common (`244,116,033`) -- decimal, not octal.
    parts = [int(match.group(i), 10) for i in (1, 2, 3)]
    if any(p > 255 for p in parts):
        return None

    return "#{:02x}{:02x}{:02x}".format(*parts)
