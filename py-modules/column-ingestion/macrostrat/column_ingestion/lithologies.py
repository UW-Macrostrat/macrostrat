from dataclasses import dataclass

from .database import get_all_liths


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
    def __init__(self):
        self.liths = get_all_liths()

    def find_lith_id(self, name):
        for lith in self.liths:
            if lith.name == name:
                return lith.id
        return None

    def get_liths(self, lith_text):
        # Process the lithology text to extract information about the rock type, grainsize, color, etc.
        split_lith = lith_text.split(";")
        liths = []
        for lith in split_lith:
            lith = lith.strip().lower()
            if lith in self.liths:
                liths.append(lith)
            else:
                print(f"Warning: Lithology '{lith}' not found in database")
        return liths


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
    for word in words:
        lith_id = liths_processor.find_lith_id(word)
        if lith_id is not None:
            print(f"Found lithology: {word} (id: {lith_id})")
            return Lithology(name=word, id=lith_id)
    return None




# TODO: make this more explicit and comprehensive.
lith_att_synonyms = {
    "cross-bedded": ["cross-stratified", "cross bedded", "cross laminated"],
}
