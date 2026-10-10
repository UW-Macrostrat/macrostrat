"""Age checks run per section: positions are local to the section they belong to."""

from macrostrat.column_ingestion import notices
from macrostrat.column_ingestion.columns.parse import Column
from macrostrat.column_ingestion.columns.sections import Section
from macrostrat.column_ingestion.intervals import Interval, RelativeAge
from macrostrat.column_ingestion.units.parse import Unit
from macrostrat.column_ingestion.validation import validate_column

PRIDOLI = Interval(1, "Pridoli", 423.0, 419.2, 5, "epoch")
LOCHKOVIAN = Interval(2, "Lochkovian", 419.2, 410.8, 6, "age")
PRAGIAN = Interval(3, "Pragian", 410.8, 407.6, 6, "age")
EMSIAN = Interval(4, "Emsian", 407.6, 393.3, 6, "age")


def unit(b_pos, t_pos, b_int=None, t_int=None):
    return Unit(
        b_pos=b_pos,
        t_pos=t_pos,
        b_age=b_int and RelativeAge(b_int, 0),
        t_age=t_int and RelativeAge(t_int, 0),
    )


def codes(*sections: Section) -> list[tuple[str, str | None]]:
    col = Column(
        local_id="RR", name="Road River", col_type="section", lat=65.9, lng=-135.7
    )
    col.sections = list(sections)
    with notices.collect_notices() as collected:
        validate_column(col)
    return [(n.code, n.section) for n in collected]


def test_sections_with_overlapping_local_heights_are_not_inversions():
    # The older section sits below, but its local heights overlap the younger one's
    older = Section(orig_id="J1609", units=[unit(0, 90, PRIDOLI, LOCHKOVIAN)])
    younger = Section(orig_id="J1610", units=[unit(0, 290, PRAGIAN, EMSIAN)])
    assert codes(younger, older) == []


def test_an_inversion_within_a_section_is_still_reported():
    inverted = Section(
        orig_id="J1610",
        units=[unit(0, 10, PRAGIAN), unit(10, 20, PRIDOLI)],
    )
    assert ("age-inversion", "J1610") in codes(inverted)


def test_each_section_needs_its_own_two_tie_points():
    dated = Section(orig_id="J1609", units=[unit(0, 90, PRIDOLI, LOCHKOVIAN)])
    one_tie = Section(orig_id="J1610", units=[unit(0, 290, PRAGIAN)])
    assert codes(dated, one_tie) == [("insufficient-age-constraints", "J1610")]
