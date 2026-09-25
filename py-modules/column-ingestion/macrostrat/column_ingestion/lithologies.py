import re
from dataclasses import dataclass
from enum import Enum

from macrostrat.utils import get_logger

from .database import get_all_lith_attributes, get_all_liths

log = get_logger(__name__)


@dataclass
class LithAtt:
    name: str
    id: int

    def __hash__(self):
        return hash(self.id)


class LithAbundance(Enum):
    """Enum for lithology abundance types."""

    DOMINANT = "dom"
    SUBSIDIARY = "sub"

    @classmethod
    def from_str(cls, value: str):
        # Handle synonyms
        if value == "major":
            return LithAbundance.DOMINANT
        elif value == "minor":
            return LithAbundance.SUBSIDIARY
        return cls[value]


@dataclass
class Lithology:
    name: str
    id: int
    attributes: set[LithAtt] | None = None
    dom: LithAbundance | None = None
    prop: float | None = None

    def __hash__(self):
        """Hash the lithology based on its id and attributes. This allows us to compare lithologies in tests without worrying about object identity."""
        return hash((self.id, frozenset(self.attributes) if self.attributes else None))


class LithsProcessor:
    liths = []
    atts = []

    # The synonyms every dataset gets. Held in code for now and planned to move into the
    # database; a dataset with its own vocabulary passes `lith_synonyms` /
    # `lith_attribute_synonyms` to the constructor instead of editing these.
    default_lith_synonyms = {
        "volcanic": ["volcanics", "lava"],
        "metavolcanic": ["metavolcanics"],
        "igneous": ["granitic"],
        "evaporite": ["gypsum-anhydrite"],
    }

    #: Source terms that mean an **attribute plus a lithology**, rewritten before parsing.
    #:
    #: `lith_synonyms` cannot express these. It substitutes inside `find_lith`, which then
    #: searches the result for a lithology only — so `porphyry -> porphyritic plutonic`
    #: yields nothing, because `_find_target` accumulates words from the start and neither
    #: `porphyritic` nor `porphyritic plutonic` is a lith name. Rewriting the text *before*
    #: the attribute/lithology loop lets the normal machinery read the attribute and then
    #: the rock, which is the whole point: `porphyry` is a porphyritic plutonic rock, not a
    #: rock Macrostrat is missing a name for.
    #:
    #: Applied on word boundaries and anywhere in the term, so a qualifier survives:
    #: `andesitic porphyry` becomes `andesitic porphyritic plutonic`.
    default_lith_rewrites: dict[str, str] = {}

    default_lith_attribute_synonyms = {
        "cross-bedded": ["cross-stratified", "cross bedded", "cross laminated"],
        "regularly bedded": ["bedded"],
        # `fine` and `coarse` are `grains`-type attributes; the hyphenated
        # compounds are how most sources actually write them.
        "fine": ["fine-grained", "fine grained"],
        "coarse": ["coarse-grained", "coarse grained"],
    }

    def __init__(
        self,
        db,
        *,
        lith_synonyms: dict[str, list[str]] | None = None,
        lith_attribute_synonyms: dict[str, list[str]] | None = None,
        lith_rewrites: dict[str, str] | None = None,
    ):
        """A processor for one dataset's lithology text.

        `lith_synonyms` and `lith_attribute_synonyms` are a dataset's own vocabulary,
        merged over the defaults as `{canonical: [source term, ...]}` — the same shape as
        the class defaults. A dataset that writes `glutenite` where Macrostrat says
        `conglomerate` supplies that here and the term then resolves like any other,
        attributes and all, rather than being special-cased at the call site.

        Merged per key, so a dataset adds terms to a canonical name the defaults already
        carry instead of replacing its list.
        """
        self.liths = get_all_liths(db)
        self.atts = get_all_lith_attributes(db)
        self.lith_synonyms = _merge_synonyms(self.default_lith_synonyms, lith_synonyms)
        self.lith_attribute_synonyms = _merge_synonyms(
            self.default_lith_attribute_synonyms, lith_attribute_synonyms
        )
        # Flattened and ordered once. `_replace_synonyms` runs on every word-step of
        # every match, so building this per call made the whole processor measurably
        # slower as soon as a loaded crosswalk pushed the list past a handful of entries.
        self._lith_synonym_order = _synonym_order(self.lith_synonyms)
        self._lith_attribute_synonym_order = _synonym_order(
            self.lith_attribute_synonyms
        )
        self.lith_rewrites = {**self.default_lith_rewrites, **(lith_rewrites or {})}
        # Longest source first, so a longer phrase is not pre-empted by a shorter one
        # inside it, and compiled once — this runs on every entity of every unit.
        self._rewrites = [
            (re.compile(rf"\b{re.escape(source)}\b"), target)
            for source, target in sorted(
                self.lith_rewrites.items(), key=lambda kv: len(kv[0]), reverse=True
            )
        ]

    def __call__(self, lith_text: str | None, type=None) -> set[Lithology]:
        return self.process_text(lith_text, type)

    def process_text(self, lith: str | None, type=None) -> set[Lithology]:
        # Process the lithology string to extract information about the rock type, grainsize, color, etc.
        output = set()

        if lith is None:
            return output

        split_lith = split_domains(lith)
        for lith in split_lith:
            res = self.process_domain(lith.strip().lower())
            output.update(res)
        for lith in output:
            if lith.dom is None:
                lith.dom = type

        return output

    def process_domain(self, lith_text) -> set[Lithology]:
        """
        Process a single lithology block that doesn't have a strong separator (semicolon) from other lithologies.
        It looks for a single lithology and any attributes that are associated with it.
        However, if multiple lithologies are found, the same attributes will be applied to all of them.
        """

        liths = set()
        atts = set()

        log.debug(f"Processing lithology domain: {lith_text}")

        candidate_entities = [x.strip() for x in lith_text.split(",")]

        for entity in candidate_entities:
            # Start searching for attributes first, then lithologies
            remaining_text = self.apply_rewrites(entity)
            log.debug(f"Entity: {remaining_text}")
            while len(remaining_text) > 0:
                # Every pass must consume at least one word, or the loop does not end.
                #
                # It is possible for a pass to consume nothing *and* leave the text
                # changed, because a synonym can be longer than the term it replaces.
                # `thin bedded-massive` is the case that found this: `bedded-massive`
                # expands to `regularly bedded-massive` through the `bedded` synonym,
                # matches neither an attribute nor a lithology, and the word-advance below
                # then strips `regularly` back off — returning the text to exactly where it
                # started, forever. Counting words is what makes the exit unconditional.
                words_before = len(remaining_text.split())
                att = None
                lith, remaining_text1 = self.find_lith(remaining_text)
                if lith is not None:
                    # If we find a lithology that consumes the entire remaining text, we can stop searching for attributes and just add the lithology.
                    # This handles special cases like "calcareous ooze" which is its own lithology, despite having the word "calcareous" which is also an attribute.
                    if len(atts) > 0:
                        lith.attributes = atts
                        atts = set()  # reset attributes after applying to a lithology
                    liths.add(lith)
                    remaining_text = remaining_text1
                    log.debug(
                        "Found lith: %s, remaining text: %s", lith, remaining_text
                    )
                else:
                    # Otherwise, we search for attributes.
                    att, remaining_text0 = self.find_lith_attribute(remaining_text)
                    log.debug("Found att: %s, remaining text: %s", att, remaining_text0)

                    remaining_text = remaining_text0
                    if att is not None:
                        atts.add(att)
                # Now search for lithologies. If we find one, we reset the attribute list.
                lith, remaining_text = self.find_lith(remaining_text)
                if lith is None and att is None:
                    # If we can't find a lithology or attribute, we advance to the next word to continue the search
                    remaining_text = " ".join(remaining_text.split()[1:])
                elif lith is not None:
                    if len(atts) > 0:
                        lith.attributes = atts
                        atts = set()  # reset attributes after applying to a lithology
                    liths.add(lith)

                if len(remaining_text.split()) >= words_before:
                    # No progress. Drop a word so the loop is guaranteed to terminate;
                    # see the note at the top of the loop.
                    remaining_text = " ".join(remaining_text.split()[1:])

            # Once we've consumed all text in this entity, we can move to the next entity

        return liths

    def apply_rewrites(self, text: str) -> str:
        """Rewrite source terms that mean an attribute plus a lithology.

        See `default_lith_rewrites`. Each source is replaced at most once so a rewrite
        whose target contains its own source cannot loop.
        """
        for pattern, target in self._rewrites:
            text, count = pattern.subn(target, text)
            if count:
                log.debug("Rewrote to: %s", text)
        return text

    def match_lith(self, name) -> Lithology | None:
        return _match_target(name, self.liths)

    def match_lith_attribute(self, name) -> LithAtt | None:
        return _match_target(name, self.atts)

    def find_lith_attribute(
        self, text, use_synonyms: bool = True
    ) -> tuple[LithAtt | None, str]:
        """Start consuming text word by word, and check for matches at each step.
        This allows us to match multi-word attributes like "cross-bedded" or "brownish gray
        """
        if use_synonyms:
            text = _replace_synonyms(text, self._lith_attribute_synonym_order)
        res, remaining_text = _find_target(text, self.atts)
        if res is not None:
            res = LithAtt(
                name=res.name, id=res.id
            )  # create a new LithAtt object without attributes for now
        return res, remaining_text

    def find_lith(
        self, text, use_synonyms: bool = True
    ) -> tuple[Lithology | None, str]:
        """Start consuming text word by word, and check for matches at each step.
        This allows us to match multi-word lithologies like "mixed carbonate-siliciclastic".
        """
        if use_synonyms:
            text = _replace_synonyms(text, self._lith_synonym_order)
        res, remaining_text = _find_target(text, self.liths)
        if res is not None:
            res = Lithology(
                name=res.name, id=res.id
            )  # create a new Lithology object without attributes for now
        return res, remaining_text


def _merge_synonyms(
    defaults: dict[str, list[str]], extra: dict[str, list[str]] | None
) -> dict[str, list[str]]:
    """Defaults plus a dataset's own, merged per canonical name rather than replaced."""
    merged = {key: list(values) for key, values in defaults.items()}
    for key, values in (extra or {}).items():
        merged.setdefault(key, [])
        merged[key] += [v for v in values if v not in merged[key]]
    return merged


def _synonym_order(synonyms_dict: dict[str, list[str]]) -> list[tuple[str, str]]:
    """`[(synonym, canonical), ...]`, longest synonym first.

    Longest first so a longer term is never shadowed by a shorter one that happens to be
    its prefix. Without the ordering the result would depend on dict order, which is
    tolerable for a handful of hand-written entries and not for a loaded crosswalk.
    """
    return sorted(
        (
            (synonym, key)
            for key, synonyms in synonyms_dict.items()
            for synonym in synonyms
        ),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )


def _replace_synonyms(text, synonym_order: list[tuple[str, str]]):
    for synonym, key in synonym_order:
        if text.startswith(synonym):
            # Replace the synonym with the key, keeping the rest of the text after it
            return key + text[len(synonym) :]
    return text


def _match_target(name, liths):
    for lith in liths:
        if lith.name == name:
            return lith
    return None


def _find_target(text, target_list) -> tuple[Lithology | LithAtt | None, str]:
    """Start consuming text word by word, and check for matches at each step.
    Return the first match found, along with remaining text that was not part of the match.
    This allows us to match multi-word lithologies like "mixed carbonate-siliciclastic" or attributes like "brownish gray".
    """
    remaining_words = text.split()
    text_to_match = []
    while len(remaining_words) > 0:
        text_to_match.append(remaining_words.pop(0))
        candidate = " ".join(text_to_match)
        res = _match_target(candidate, target_list)
        if res is not None:
            return res, " ".join(remaining_words)
    # Return None if no match was found, along with an empty string for remaining text
    return None, text


split_words = {"and", "or"}


def split_domains(text) -> list[str]:
    """Splits text into parts within which we will search for lithologies and attributes."""
    for split_word in split_words:
        text = text.replace(f" {split_word} ", ";")
    return text.split(";")


class MultipleLithologiesError(ValueError):
    pass
