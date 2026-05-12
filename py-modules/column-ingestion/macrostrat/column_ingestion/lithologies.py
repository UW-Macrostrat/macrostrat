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

    # TODO: make this more explicit and comprehensive. Consider adding to database.
    lith_synonyms = {}

    lith_attribute_synonyms = {
        "cross-bedded": ["cross-stratified", "cross bedded", "cross laminated"],
        "regularly bedded": ["bedded"],
    }

    def __init__(self):
        self.liths = get_all_liths()
        self.atts = get_all_lith_attributes()

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
            remaining_text = entity
            log.debug(f"Entity: {remaining_text}")
            while len(remaining_text) > 0:
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

            # Once we've consumed all text in this entity, we can move to the next entity

        return liths

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
            text = _replace_synonyms(text, self.lith_attribute_synonyms)
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
            text = _replace_synonyms(text, self.lith_synonyms)
        res, remaining_text = _find_target(text, self.liths)
        if res is not None:
            res = Lithology(
                name=res.name, id=res.id
            )  # create a new Lithology object without attributes for now
        return res, remaining_text


def _replace_synonyms(text, synonyms_dict):
    for key, synonyms in synonyms_dict.items():
        for synonym in synonyms:
            if text.startswith(synonym):
                # Replace the synonym with the key, but keep the rest of the text after the synonym
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


liths_processor = LithsProcessor()

split_words = {"and", "or"}


def split_domains(text) -> list[str]:
    """Splits text into parts within which we will search for lithologies and attributes."""
    for split_word in split_words:
        text = text.replace(f" {split_word} ", ";")
    return text.split(";")


class MultipleLithologiesError(ValueError):
    pass
