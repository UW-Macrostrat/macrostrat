"""The format's proportion syntax, shared by lithologies and facies.

An entry may end in a parenthesised proportion — `sandstone (60%)`, `shale (0.4)`,
`reef (major)` — which is a number between 0 and 1, a percentage, or a qualitative
term (`major` / `minor`, or the database's `dom` / `sub`). Entries without one share
whatever is left equally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TRAILING_PROPORTION = re.compile(r"^(?P<body>.*?)\s*\((?P<prop>[^()]*)\)\s*$")

#: Qualitative terms and the abundance they mean, in the vocabulary of `unit_liths.dom`.
ABUNDANCE_TERMS = {"major": "dom", "dom": "dom", "minor": "sub", "sub": "sub"}


@dataclass(frozen=True)
class Proportion:
    #: A fraction in [0, 1], when the entry gave a number.
    value: float | None = None
    #: `dom` or `sub`, when the entry gave a term (or implied one).
    abundance: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.value is None and self.abundance is None


def split_proportion(text: str) -> tuple[str, Proportion, str | None]:
    """Split a trailing `(…)` off an entry.

    Returns the entry without it, the proportion it expressed, and the raw text when it
    could not be read (so the caller can report it) — `None` otherwise.
    """
    match = _TRAILING_PROPORTION.match(text.strip())
    if match is None:
        return text.strip(), Proportion(), None
    body = match.group("body").strip()
    raw = match.group("prop").strip()
    proportion = parse_proportion(raw)
    if proportion is None:
        return body, Proportion(), raw
    return body, proportion, None


def parse_proportion(raw: str) -> Proportion | None:
    """Read a proportion expression; `None` when it is not one."""
    text = raw.strip().lower()
    if text == "":
        return Proportion()
    if text in ABUNDANCE_TERMS:
        return Proportion(abundance=ABUNDANCE_TERMS[text])
    percent = text.endswith("%")
    number = text.rstrip("%").strip()
    try:
        value = float(number)
    except ValueError:
        return None
    if percent or value > 1:
        value = value / 100
    if not 0 <= value <= 1:
        return None
    return Proportion(value=value)


def share_remaining(proportions: list[Proportion]) -> list[float]:
    """Resolve a list of proportions to fractions summing to 1.

    Numbers are kept; entries without one share what the numbers leave, equally.
    A term alone says nothing about the fraction, so it is treated as unstated.
    """
    stated = [p.value for p in proportions if p.value is not None]
    unstated = len(proportions) - len(stated)
    remaining = max(0.0, 1.0 - sum(stated))
    out = []
    for p in proportions:
        if p.value is not None:
            out.append(p.value)
        elif unstated > 0:
            out.append(remaining / unstated)
    return out
