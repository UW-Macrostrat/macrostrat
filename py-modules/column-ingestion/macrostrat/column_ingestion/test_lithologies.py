from dataclasses import dataclass

from pytest import mark

from .lithologies import Lithology, LithAtt, process_liths_text


@dataclass
class LithologyTestCase:
    input: str
    output: set[Lithology]

sandstone = Lithology(name="sandstone", id=10)
limestone = Lithology(name="limestone", id=30)
cross_bedded_sandstone = Lithology(
    name="sandstone",
    id=10,
    attributes={LithAtt(name="cross-bedded", id=17)}
)

test_cases = [
    LithologyTestCase("sandstone", {sandstone}),
    LithologyTestCase("limestone; sandstone", {sandstone, limestone}),
    LithologyTestCase("cross-bedded sandstone", {cross_bedded_sandstone}),
    LithologyTestCase("limestone; cross-bedded sandstone", {limestone, cross_bedded_sandstone}),
]

@mark.parametrize("test_case", test_cases)
def test_process_liths_text(test_case):
    liths = process_liths_text(test_case.input)
    assert liths == test_case.output
