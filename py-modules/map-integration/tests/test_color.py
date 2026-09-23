"""The colour encodings staging tables actually arrive in.

Every case here is drawn from `sources.ngs_polygons`, which carries all of them
at once -- see `macrostrat.map_integration.utils.color`.
"""

import pytest

from macrostrat.map_integration.utils.color import normalize_color


@pytest.mark.parametrize(
    "value,expected",
    [
        # Hex passes through, normalized to lowercase; `#abc` expands.
        ("#AABBCC", "#aabbcc"),
        ("aabbcc", "#aabbcc"),
        ("#abc", "#aabbcc"),
        # The GeMS `areafillrgb` encodings, all four bracketings.
        ("255,255,221", "#ffffdd"),
        ("(255, 255, 77)", "#ffff4d"),
        ("rgb(255, 204, 230)", "#ffcce6"),
        ("{243,237,200}", "#f3edc8"),
        # Zero-padded components are decimal, not octal.
        ("244,116,033", "#f47421"),
        # A trailing separator, and an alpha channel with nowhere to go.
        ("255,235,169,", "#ffeba9"),
        ("(0, 8, 40, 1)", "#000828"),
        # Nine digits are three zero-padded components run together.
        ("249115087", "#f97357"),
        # Refused rather than guessed: out of range, negative, or not a colour.
        ("268,244,182", None),
        ("(-38, 217, 166)", None),
        ("junk", None),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_color(value, expected):
    assert normalize_color(value) == expected
