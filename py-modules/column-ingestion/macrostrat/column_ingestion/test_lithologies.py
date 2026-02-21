from dataclasses import dataclass

from pytest import mark

from .lithologies import LithAtt, Lithology, process_liths_text


@dataclass
class LithologyTestCase:
    input: str
    output: set[Lithology]
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
]


@mark.parametrize("test_case", test_cases)
def test_process_liths_text(test_case):
    liths = process_liths_text(test_case.input)
    assert liths == test_case.output
