from dataclasses import dataclass, field

from pytest import fixture, mark

from macrostrat.column_ingestion.lithologies import LithAtt, Lithology, LithsProcessor


@dataclass
class LithologyDescription:
    name: str
    attributes: set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self.name) + hash(frozenset(self.attributes))


@dataclass
class LithologyTestCase:
    input: str
    output: set[Lithology | LithologyDescription]
    expect_error: bool = False


sandstone = Lithology(name="sandstone", id=10)
limestone = Lithology(name="limestone", id=30)
cross_bedded_sandstone = Lithology(
    name="sandstone", id=10, attributes={LithAtt(name="cross-bedded", id=17)}
)
cross_bedded_red_sandstone = Lithology(
    name="sandstone",
    id=10,
    attributes={LithAtt(name="cross-bedded", id=17), LithAtt(name="red", id=112)},
)
stromatolitic_dolomite = Lithology(
    name="dolomite", id=31, attributes={LithAtt(name="stromatolitic", id=78)}
)
dolomite = Lithology(name="dolomite", id=31)
chert = Lithology(name="chert", id=45)
sand = Lithology(name="sand", id=3)
mixed_carbonate = Lithology(name="mixed carbonate-siliciclastic", id=17)

lenticular = LithAtt(name="lenticular", id=1)
regularly_bedded = LithAtt(name="regularly bedded", id=6)
bioclastic = LithAtt(name="bioclastic", id=145)

carbonate_test_case = {
    Lithology(name="carbonate", id=18, attributes={lenticular}),
    Lithology(
        name="carbonate",
        id=18,
        attributes={
            bioclastic,
            lenticular,
        },
    ),
    Lithology(
        name="carbonate",
        id=18,
        attributes={regularly_bedded},
    ),
}


@mark.parametrize("lith_att", [lenticular, regularly_bedded, bioclastic])
def test_lith_atts_found(test_db, lith_att):
    name = test_db.run_query(
        "SELECT lith_att FROM macrostrat.lith_atts WHERE id = :lith_att_id",
        dict(lith_att_id=lith_att.id),
    ).scalar()
    assert name == lith_att.name


test_cases = [
    LithologyTestCase("sandstone", {sandstone}),
    LithologyTestCase("limestone; sandstone", {sandstone, limestone}),
    LithologyTestCase("cross-bedded sandstone", {cross_bedded_sandstone}),
    LithologyTestCase(
        "limestone; cross-bedded sandstone", {limestone, cross_bedded_sandstone}
    ),
    LithologyTestCase("cross-bedded, red sandstone", {cross_bedded_red_sandstone}),
    LithologyTestCase(
        "cross-bedded, red sandstone; stromatolitic dolomite",
        {cross_bedded_red_sandstone, stromatolitic_dolomite},
    ),
    LithologyTestCase("stromatolitic dolomite", {stromatolitic_dolomite}),
    #  "stromatoporoid" is not a valid attribute right now)
    # TODO: print a warning for unrecognized attributes, or return them
    LithologyTestCase("stromatoporoid dolomite", {dolomite}),
    # Handle common case where multiple liths are listed with commas instead of semicolons
    LithologyTestCase(
        "dolomite, limestone, chert, cross-bedded sandstone",
        {dolomite, limestone, chert, cross_bedded_sandstone},
    ),
    # Play around with some special cases for separators
    LithologyTestCase(
        "dolomite; limestone; chert; cross-bedded, red sandstone",
        {dolomite, limestone, chert, cross_bedded_red_sandstone},
    ),
    LithologyTestCase(
        "dolomite, limestone, chert; cross-bedded, red sandstone",
        {dolomite, limestone, chert, cross_bedded_red_sandstone},
    ),
    LithologyTestCase(
        "dolomite, limestone, chert, cross-bedded, red sandstone",
        {dolomite, limestone, chert, cross_bedded_red_sandstone},
    ),
    LithologyTestCase(
        "cross-bedded sandstone and chert", {cross_bedded_sandstone, chert}
    ),
    LithologyTestCase("mixed carbonate-siliciclastic", {mixed_carbonate}),
    LithologyTestCase("some rocks and stuff", set()),
    LithologyTestCase(
        "fractured, brownish gray siltstone, sand, and mixed carbonate-siliciclastic",
        {
            mixed_carbonate,
            sand,
            Lithology(
                name="siltstone",
                id=9,
                attributes={
                    LithAtt(name="fractured", id=169),
                    LithAtt(name="brownish gray", id=133),
                },
            ),
        },
    ),
    LithologyTestCase(
        "calcareous sandstone",
        {
            calcareous_sandstone := Lithology(
                name="sandstone", id=10, attributes={LithAtt(name="calcareous", id=80)}
            )
        },
    ),
    LithologyTestCase(
        "calcareous ooze",
        {calcareous_ooze := Lithology(name="calcareous ooze", id=104)},
    ),
    # Synonyms
    LithologyTestCase(
        "cross-stratified grainstone",
        {
            cross_bedded_grainstone := Lithology(
                name="grainstone",
                id=23,
                attributes={LithAtt(name="cross-bedded", id=17)},
            )
        },
    ),
    LithologyTestCase(
        "lenticular carbonate; bioclastic lenticular carbonate; bedded carbonate",
        carbonate_test_case,
    ),
    LithologyTestCase(
        "lenticular carbonate; bioclastic, lenticular carbonate; regularly bedded carbonate",
        carbonate_test_case,
    ),
    # Test cases that rely on the database to resolve ambiguities or get IDs for attributes
    LithologyTestCase(
        "tabular, thickly bedded, cross-bedded sandstone; flute casts siltstone",
        output1 := {
            LithologyDescription(
                name="sandstone",
                attributes={"tabular", "thickly bedded", "cross-bedded"},
            ),
            LithologyDescription(name="siltstone", attributes={"flute casts"}),
        },
    ),
    # Be resilient to extra commas
    LithologyTestCase(
        "tabular, thickly bedded, cross-bedded, sandstone; flute casts, siltstone",
        output1,
    ),
    # --- lith synonyms -----------------------------------------------------
    LithologyTestCase("Volcanics", {LithologyDescription(name="volcanic")}),
    LithologyTestCase("Lava", {LithologyDescription(name="volcanic")}),
    LithologyTestCase("Metavolcanics", {LithologyDescription(name="metavolcanic")}),
    LithologyTestCase("Granitic", {LithologyDescription(name="igneous")}),
    LithologyTestCase("Gypsum-Anhydrite", {LithologyDescription(name="evaporite")}),
    # --- hyphenated grainsize attributes -----------------------------------
    LithologyTestCase(
        "Fine-grained sandstone",
        {LithologyDescription(name="sandstone", attributes={"fine"})},
    ),
    LithologyTestCase(
        "Coarse-grained sandstone",
        {LithologyDescription(name="sandstone", attributes={"coarse"})},
    ),
    # A synonym must not shadow a longer real term that contains it. Adding
    # `aus conglomerat` as a synonym once broke `Aus conglomerate` outright.
    LithologyTestCase("Aus conglomerate", {LithologyDescription(name="conglomerate")}),
]


@fixture(scope="class")
def processor(test_db):
    yield LithsProcessor(test_db)


def validate_lith_attribute(test_db, lith_att: str) -> LithAtt:
    """Expand a LithAtt description to a full LithAtt object with ID, using the database."""
    att_id = test_db.run_query(
        "SELECT id FROM macrostrat.lith_atts WHERE lith_att = :lith_att",
        dict(lith_att=lith_att),
    ).scalar()
    if att_id is None:
        raise ValueError(f"Lithology attribute {lith_att} not found in database")
    return LithAtt(name=lith_att, id=att_id)


def validate_lithology_description(
    db, lithology: Lithology | LithologyDescription
) -> Lithology:
    """Expand a LithologyDescription to a full Lithology object with ID and attributes, using the database."""
    if isinstance(lithology, Lithology):
        return lithology

    lith_id = db.run_query(
        "SELECT id FROM macrostrat.liths WHERE lith = :lith",
        dict(lith=lithology.name),
    ).scalar()
    if lith_id is None:
        raise ValueError(f"Lithology {lithology.name} not found in database")

    attrs = {validate_lith_attribute(db, att_name) for att_name in lithology.attributes}
    if len(attrs) == 0:
        attrs = None

    return Lithology(id=lith_id, name=lithology.name, attributes=attrs)


def test_a_synonym_longer_than_its_term_still_terminates(processor):
    """`thin bedded-massive` used to hang the processor outright.

    `bedded-massive` expands to `regularly bedded-massive` through the `bedded` synonym,
    matches neither an attribute nor a lithology, and the word-advance at the foot of the
    loop then strips `regularly` back off — returning the text to exactly where it
    started. A synonym longer than the term it replaces can undo the loop's only progress
    step, so `process_domain` counts words instead of trusting the text to shrink.

    Real GBDB input, and it would have hung the ingest rather than only a measurement.
    """
    assert processor.process_text("thin bedded-massive") == set()


def test_supplied_synonyms_merge_over_the_defaults(test_db):
    """A dataset's own vocabulary resolves like any other term, attributes included.

    The point of loading a crosswalk rather than special-casing at the call site: a
    crosswalked name is substituted before matching, so anything else in the string is
    still read normally.
    """
    processor = LithsProcessor(test_db, lith_synonyms={"conglomerate": ["glutenite"]})

    assert {lith.name for lith in processor.process_text("glutenite")} == {
        "conglomerate"
    }
    fine = processor.process_text("fine glutenite")
    assert {lith.name for lith in fine} == {"conglomerate"}
    assert {att.name for lith in fine for att in (lith.attributes or set())} == {"fine"}
    # The defaults are still there rather than replaced.
    assert "volcanic" in processor.lith_synonyms


def test_a_rewrite_reads_a_term_as_an_attribute_plus_a_lithology(test_db):
    """Some source terms mean a rock *and* a modifier, which a synonym cannot express.

    `porphyry` is a porphyritic plutonic rock, not a rock Macrostrat lacks a name for. A
    `lith_synonyms` entry fails here because it substitutes inside `find_lith`, which then
    searches the result for a lithology only — `porphyritic plutonic` leads with an
    attribute, so nothing matches. Rewriting before the parse loop lets the normal
    machinery read the attribute and then the rock.
    """
    processor = LithsProcessor(
        test_db, lith_rewrites={"porphyry": "porphyritic plutonic"}
    )

    liths = processor.process_text("porphyry")
    assert {lith.name for lith in liths} == {"plutonic"}
    assert {att.name for lith in liths for att in (lith.attributes or set())} == {
        "porphyritic"
    }

    # Applied on word boundaries and anywhere in the term, so a qualifier survives and
    # still contributes whatever it matches.
    qualified = processor.process_text("quartz porphyry")
    assert {lith.name for lith in qualified} == {"plutonic"}
    assert "porphyritic" in {
        att.name for lith in qualified for att in (lith.attributes or set())
    }


@mark.parametrize("test_case", test_cases)
def test_process_liths_text(processor, test_db, test_case):
    # We have to depend on the database to get the IDs for the lithologies
    liths = processor.process_text(test_case.input)
    output = {
        validate_lithology_description(test_db, lith) for lith in test_case.output
    }
    assert liths == output
