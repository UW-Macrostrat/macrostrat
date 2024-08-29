"""
Cleaning functions for stratigraphic names based on John Husson's work from 2016
"""

import enum
import re
from functools import reduce
from string import punctuation

from pydantic import BaseModel

from ...database import get_db


class Confidence(enum.Enum):
    Low = "low"
    High = "high"
    NotIndicated = "not indicated"


def clean_strat_name_text(text):
    names = clean_strat_name(text, split_names=False)
    if len(names) == 0:
        return None
    assert len(names) == 1
    return names[0].name


def clean_strat_name(text, split_names=True):

    # Remove gremlins
    for g in gremlins:
        text = text.replace(g, gremlins[g])

    # Standardize Unicode to ASCII and convert to lowercase
    text = text.encode("ascii", "ignore").decode().lower()

    confidence = Confidence.NotIndicated

    # Strip parenthetical text, which is often confidence information
    # denoted by a question mark
    matches = re.findall(r"\((.+?)\)", text)
    for match in matches:
        text = text.replace(match, ";")
        if "?" in match:
            confidence = Confidence.Low

    names = [text]
    if split_names:
        names = _split_names(text)

    # Concatenate the cleaned names
    return reduce(
        lambda x, y: x + y,
        (list(_clean_name(name, confidence=confidence)) for name in names),
        [],
    )


def _clean_name(name, confidence=Confidence.NotIndicated):
    global _ignore_list
    if _ignore_list is None:
        _ignore_list = build_ignore_list()

    # Remove punctuation
    for d in delete:
        name = name.replace(d, " ")

    # Collapse whitespace
    name = " ".join(name.split())

    # Get list of tokens
    rank = None
    tokens = name.split()
    collected_text = []
    for token in tokens:
        if token.endswith("?"):
            confidence = Confidence.Low
            token = token[:-1]
        # Replace abbreviations
        if token in replace:
            token = replace[token]
        # If token should be ignored
        if token in _ignore_list:
            continue
        _rank = get_rank_signifier(token)
        if _rank is not None or token in stop_words:
            rank = _rank
            if len(collected_text) > 0:
                yield StratNameTextMatch(
                    name=" ".join(collected_text), rank=rank, confidence=confidence
                )
                collected_text = []
        else:
            collected_text.append(token)
    # Put any remaining tokens in a match
    if len(collected_text) > 0:
        yield StratNameTextMatch(
            name=" ".join(collected_text), rank=rank, confidence=confidence
        )


def _split_names(name) -> list[str]:
    """Split a stratigraphic name on one of several common delimiters."""
    acc = ""
    out = []
    for char in name:
        if char in [";", "|", "-", "–", "—", "-", "\\", "&", "/", ","]:
            out.append(acc)
            acc = ""
        else:
            acc += char
    out.append(acc)
    return [x.strip() for x in out if x.strip() != ""]


class StratRank(enum.Enum):
    Supergroup = "sgp"
    Group = "gp"
    Formation = "fm"
    Member = "mbr"
    Bed = "bed"
    Series = "series"
    Assemblage = "assemblage"
    Suite = "suite"

    def __lt__(self, other):

        return order.index(self) < order.index(other)

    def __repr__(self):
        return self.value.capitalize()


class StratNameTextMatch(BaseModel):
    name: str
    rank: StratRank | None
    confidence: Confidence
    # Extra information about lithology and age
    # lith_signifiers: list[str]
    # age_signifiers: list[str]

    # Sort by name
    def __lt__(self, other):
        order = [
            StratRank.Member,
            StratRank.Formation,
            StratRank.Series,
            StratRank.Group,
            StratRank.Bed,
            StratRank.Assemblage,
            StratRank.Supergroup,
            StratRank.Suite,
            None,
        ]
        ix = order.index(self.rank)
        other_ix = order.index(other.rank)
        if ix == other_ix:
            return self.name < other.name
        return ix < other_ix

    def __hash__(self):
        return hash(self.name) + hash(self.rank)

    def __eq__(self, other):
        if self.rank is None or other.rank is None:
            return self.name == other.name
        return self.name == other.name and self.rank == other.rank

    def __ne__(self, other):
        return not self.__eq__(other)

    def __rich_repr__(self):
        yield self.name
        if self.rank is not None:
            yield "rank", self.rank


def format_name(name: StratNameTextMatch):
    if name.rank is None:
        return name.name
    return f"[bold]{name.name}[/bold] ({name.rank.value})"


def get_rank_signifier(text: str) -> StratRank | None:
    if text in ["fmt", "formation", "fm"]:
        return StratRank.Formation
    if text in ["group", "gr", "gp", "grp"]:
        return StratRank.Group
    if text in ["sgp", "supergroup", "sgroup", "supergrp"]:
        return StratRank.Supergroup
    if text in ["member", "mbr", "mem", "memb"]:
        return StratRank.Member
    if text in ["bed"]:
        return StratRank.Bed
    try:
        return StratRank(text)
    except ValueError:
        # Try removing any trailing 's' to see if it's a rank
        return None


# DESIGNATIONS OF STRATIGRAPHIC RANK
ranks = [
    "fm",
    "fmt",
    "formation",
    "group",
    "gp",
    "gr",
    "grp",
    "member",
    "mbr",
    "mem",
    "memb",
    "unit",
    "series",
    "assemblage",
    "suite",
    "supergroup",
]

_ignore_list = None


# DESIGNATIONS OF STRATIGRAPHIC RANK (SEDIMENTARY LITHOLOGIES)
def build_ignore_list():
    db = get_db()
    ignore = [
        l[0] for l in db.run_query("SELECT lith name FROM macrostrat.liths").all()
    ]

    ignore += ["ls", "dol", "dolo", "ss", "cong", "congl", "sh"]

    # IGNEOUS TERMS
    ignore += [
        "pluton",
        "complex",
        "granitoids",
        "granitoid",
        "massif",
        "batholith",
        "dyke",
        "dykes",
        "dike",
        "dikes",
    ]

    # POSITIONAL TERMS
    ignore += ["lower", "upper", "middle", "basal"]

    # Stop words
    ignore += stop_words

    return ignore


# STRINGS TO BE DELETED
delete = [l for l in punctuation if l not in ["-", "/", "?"]]

# SOME INSTANCES DIVIDE STRAT NAMES ON WITH THESE MODIFIERS
to_split = ["\s*-\s*", "\s*/\s*"]

# ABBREVIATION REPLACEMENTS
replace = {
    "mtn": "mountain",
    "mt": "mountain",
    "mtns": "mountains",
    "ft": "fort",
    "pk": "peak",
    "ste": "saint",
    "canyn": "canyon",
    "st": "saint",
}

stop_words = ["of", "and", "or"]

# NEED ZAPPING
gremlins = {
    "\x02": " ",
    "\x03": "",
    "\x01": "",
    "\x19": "",
    "\x06\x08\x13\x11\x08\x12": "",
}
