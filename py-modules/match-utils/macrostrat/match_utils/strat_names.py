"""
Cleaning functions for stratigraphic names

- Parts are based on John Husson's original code from 2016

"""

import enum
import re
from contextvars import ContextVar
from functools import reduce
from string import punctuation

from pydantic import BaseModel


class Confidence(enum.Enum):
    Low = "low"
    High = "high"
    NotIndicated = "not indicated"


_ignore_list: ContextVar[list[str] | None] = ContextVar("_ignore_list", default=None)


def create_ignore_list(lith_names: list[str], force: bool = False):
    """Create the ignore list for stratigraphic name cleaning."""
    _ignore_list.set(build_ignore_list(lith_names))


def get_ignore_list() -> list[str]:
    ignore = _ignore_list.get()
    if ignore is None:
        raise ValueError(
            "Ignore list has not been initialized; call create_ignore_list first."
        )
    return ignore


def clean_strat_name_text(text):
    names = clean_strat_name(text, split_names=False)
    if len(names) == 0:
        return None
    assert len(names) == 1
    return names[0].name


def clean_strat_name(text, split_names=True, *, split_hierarchy=False):
    """Parse a text string into the stratigraphic names it contains.

    `split_hierarchy` opts into splitting a name that names more than one unit at
    once by their relationship -- "Williamson Creek Member of the Fleming
    Formation" is a member *and* its parent formation, not one name. It is off by
    default because it changes the parse of any text containing `of`, `and` or
    `or`, and every existing caller was written against the current behaviour.

    See `_clean_name` for why this is a flag rather than a fix.
    """
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
        (
            list(
                _clean_name(
                    name, confidence=confidence, split_hierarchy=split_hierarchy
                )
            )
            for name in names
        ),
        [],
    )


def _clean_name(
    name, confidence=Confidence.NotIndicated, *, split_hierarchy: bool = False
):
    """Walk a name right-to-left, yielding each stratigraphic name it contains.

    Right-to-left is what lets a rank word terminate and label the name in front
    of it rather than being deleted out of the middle of one: "Wagon Bed
    Formation" keeps its `Bed`.

    **`split_hierarchy` and the dead reset.** `stop_words` -- `of`, `and`, `or` --
    are meant to end one name and begin another, and the `should_reset` branch
    below says so. They never do: `build_ignore_list` appends `stop_words` to the
    ignore list, and the `continue` a few lines above fires first, so the token is
    dropped and the two names run together. "Kekiktuk Conglomerate of the Endicott
    Group" parses as the single name `kekiktuk the endicott`.

    Checking separators before the ignore list restores the reset, and dropping
    articles keeps `the` out of the result. The two together are what make a
    nested name come apart into its levels, most specific last in yield order --
    which `StratNameTextMatch.__lt__` then sorts most specific first.

    It is opt-in rather than simply repaired because it changes the parse of every
    name containing a stop word, and `standardize_names` feeds SGP, MagIC and the
    match API. Measured on the 7,382 distinct NGS map legend names, it lifts the
    share matching a lexicon entry from 30.2% to 48.8%.
    """
    _ignore_list = get_ignore_list()

    # Remove punctuation. A hyphen that survived `_split_names` is inside a word,
    # and becomes a token break so each part meets the ignore list on its own --
    # `ash` in `ash-flow` is a lithology whether or not it is written solid.
    for d in delete:
        name = name.replace(d, " ")
    name = name.replace("-", " ")

    # Collapse whitespace
    name = " ".join(name.split())

    # Get list of tokens
    rank = None
    tokens = name.split()
    collected_text = []
    liths = []
    reversed_tokens = tokens[::-1]
    for position, token in enumerate(reversed_tokens):
        if token.endswith("?"):
            confidence = Confidence.Low
            token = token[:-1]
        # Replace abbreviations
        if token in replace:
            token = replace[token]
        # A separator has to be recognized before the ignore list gets to it --
        # stop words are in that list, so the `continue` below would drop it and
        # the reset that gives us the next name would never happen.
        is_separator = split_hierarchy and token in stop_words

        if not is_separator:
            # An article is dropped only where a separator put it there --
            # "of *the* Endicott Group". Walking right-to-left, that means the
            # next token we will see is the separator. Anywhere else it is part
            # of the name: `The Forks` is a formation in the lexicon.
            if split_hierarchy and token in articles:
                following = reversed_tokens[position + 1 :]
                if following and following[0] in stop_words:
                    continue
            # If token should be ignored
            if token in _ignore_list:
                if token not in non_lith_ignores:
                    liths.append(token)
                continue

        should_reset = False
        if token in stop_words:
            # Reset to form another stratigraphic name
            should_reset = True
        # determine rank from provided strat_name query parameter
        token_rank = get_rank_signifier(token)
        if rank is None and token_rank is not None:
            # Intepret as rank and continue
            rank = token_rank
            should_reset = True

        if should_reset:
            if len(collected_text) == 0:
                # No stratigraphic name
                continue
            yield StratNameTextMatch(
                name=" ".join(collected_text[::-1]),
                rank=rank,
                confidence=confidence,
                lith_signifiers=liths[::-1],
            )
            collected_text = []
            liths = []
            # If the current token is a rank, we assign it to the next stratigraphic name
            rank = token_rank
        else:
            collected_text.append(token)

    # Put any remaining tokens in a match
    if len(collected_text) == 0:
        return
    yield StratNameTextMatch(
        name=" ".join(collected_text[::-1]),
        rank=rank,
        confidence=confidence,
        lith_signifiers=liths[::-1],
    )


#: A dash that separates names, as opposed to one inside a word. Only a spaced
#: dash divides: "Granite - Cherryville pluton" names two things, "Ash-flow tuff"
#: names one.
_SPACED_DASH = re.compile(r"\s+[-\u2013\u2014]+\s+")


def _split_names(name) -> list[str]:
    """Split a stratigraphic name on one of several common delimiters.

    **An intra-word hyphen is not a delimiter.** Splitting on every `-` cut
    `Ash-flow tuff` into `ash` and `flow`, and since `ash` is a lithology and
    `flow` is not, the phrase reduced to the bare word `flow`. The lexicon was
    normalized the same way, so `Devine Canyon Ash-flow Tuff` also reduced to
    `flow` -- and the two matched each other on an artifact of the cleaner.
    Hyphens inside words now separate tokens rather than names, so that entry
    keeps its `devine canyon` and no longer collides with a description.
    """
    name = _SPACED_DASH.sub(";", name)
    acc = ""
    out = []
    for char in name:
        if char in [";", "|", "\\", "&", "/", ","]:
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

    #: Lithology words the cleaner removed from this name, in the order they
    #: appear. `Ravenswood Granodiorite` cleans to `ravenswood`, and this is
    #: where the `granodiorite` goes. It is the only surviving evidence that the
    #: text named a rock unit rather than described one, which is what
    #: distinguishes it from a description reading "gray sandstone".
    lith_signifiers: list[str] = []

    # Extra information about age
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


def format_name(name: StratNameTextMatch, use_rich=True):
    # Additional data
    data = []
    if name.rank is not None:
        data.append(name.rank.value)
    if name.confidence is Confidence.Low:
        data.append("low confidence")
    suffix = ""
    if len(data) > 0:
        suffix = " (" + ", ".join(data) + ")"
    if not use_rich:
        return f"{name.name}{suffix}"
    return f"[bold]{name.name}[/bold]{suffix}"


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


# DESIGNATIONS OF STRATIGRAPHIC RANK (SEDIMENTARY LITHOLOGIES)
def build_ignore_list(lith_names: list[str]) -> list[str]:
    ignore = lith_names

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
to_split = [r"\s*-\s*", r"\s*/\s*"]

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

#: Entries of the ignore list that are not lithologies. The ignore list mixes
#: rock names with grammar and position, and only the rock names are evidence
#: that a phrase named a unit, so these are held back from `lith_signifiers`.
non_lith_ignores = frozenset(stop_words + ["lower", "upper", "middle", "basal"])

#: Dropped only in hierarchy mode. Only ever reached there, since a separator is
#: what leaves one exposed: "of *the* Endicott Group".
#:
#: `the` alone, deliberately. `a` and `an` belong here by grammar and not by data:
#: the column-ingestion spreadsheet spec uses single-letter designations for
#: informal units -- its own examples include `Bed A` and `A Member, B Formation`
#: -- so dropping `a` silently deletes the name it is trying to clean.
#:
#: And `the` is dropped only directly after a separator, for the same reason in a
#: different shape: `The Forks` is a formation, so an article is only noise where
#: the grammar put it there rather than the name.
articles = ["the"]

# NEED ZAPPING
gremlins = {
    "\x02": " ",
    "\x03": "",
    "\x01": "",
    "\x19": "",
    "\x06\x08\x13\x11\x08\x12": "",
}
