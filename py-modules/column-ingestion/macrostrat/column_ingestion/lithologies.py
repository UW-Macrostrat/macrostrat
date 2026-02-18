from dataclasses import dataclass

from .database import get_all_liths, get_all_lith_attributes


@dataclass
class LithAtt:
    name: str
    id: int

    def __hash__(self):
        return hash(self.id)

@dataclass
class Lithology:
    name: str
    id: int
    attributes: set[LithAtt] | None = None

    def __hash__(self):
        """Hash the lithology based on its id and attributes. This allows us to compare lithologies in tests without worrying about object identity."""
        return hash((self.id, frozenset(self.attributes) if self.attributes else None))

class LithsProcessor:
    liths = []
    atts = []
    def __init__(self):
        self.liths = get_all_liths()
        self.atts = get_all_lith_attributes()

    def find_lith(self, name):
        for lith in self.liths:
            if lith.name == name:
                return Lithology(name=lith.name, id=lith.id)
        return None

    def find_lith_attribute(self, name):
        for att in self.atts:
            if att.name == name:
                return LithAtt(name=name, id=att.id)
        return None

liths_processor = LithsProcessor()

def process_liths_text(lith) -> set[Lithology] | None:
    # Process the lithology string to extract information about the rock type, grainsize, color, etc.
    split_lith = lith.split(";")
    output = set()
    for lith in split_lith:
        res = process_single_lith(lith.strip().lower())
        if res is not None:
            output.add(res)
    return output

def process_single_lith(lith_text) -> Lithology | None:
    # Split words
    words = lith_text.split()
    # Check for liths
    lith = None
    remaining_words = []
    for word in words:
        _lith = liths_processor.find_lith(word)
        if _lith is not None:
            print(f"Found lithology: {word} (id: {_lith.id})")
            if lith is not None:
                raise MultipleLithologiesError(f"Multiple lithologies found in text: '{lith_text}'")
            else:
                lith = _lith
        else:
            remaining_words.append(word)
    if lith is None:
        return None

    # Find attributes
    atts = set()
    for word in remaining_words:
        # Check for attributes
        att = liths_processor.find_lith_attribute(word)
        if att is not None:
            atts.add(att)
    if len(atts) > 0:
        lith.attributes = atts
    return lith


class MultipleLithologiesError(ValueError):
    pass



# TODO: make this more explicit and comprehensive.
lith_att_synonyms = {
    "cross-bedded": ["cross-stratified", "cross bedded", "cross laminated"],
}
