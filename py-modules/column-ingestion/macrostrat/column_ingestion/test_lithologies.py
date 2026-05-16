from dataclasses import dataclass, field

from pytest import fixture, mark

from .lithologies import LithAtt, Lithology, LithsProcessor


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

carbonate_test_case = {
    Lithology(name="carbonate", id=18, attributes={LithAtt(name="lenticular", id=1)}),
    Lithology(
        name="carbonate",
        id=18,
        attributes={
            LithAtt(name="bioclastic", id=145),
            LithAtt(name="lenticular", id=1),
        },
    ),
    Lithology(
        name="carbonate",
        id=18,
        attributes={LithAtt(name="regularly bedded", id=6)},
    ),
}


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
]


@fixture(scope="session")
def processor(test_db_macrostrat_schema_only):
    yield LithsProcessor(test_db_macrostrat_schema_only)


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


@mark.parametrize("test_case", test_cases)
def test_process_liths_text(processor, test_db, test_case):
    # We have to depend on the database to get the IDs for the lithologies
    liths = processor.process_text(test_case.input)
    output = {
        validate_lithology_description(test_db, lith) for lith in test_case.output
    }
    assert liths == output
