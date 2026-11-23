from macrostrat.column_ingestion import Column, Section, Unit
from macrostrat.column_ingestion.ingest import _thickness_from_positions


def _column(axis_type, *units):
    return Column(
        local_id="1",
        name="Test",
        axis_type=axis_type,
        sections=[Section(units=list(units))],
    )


def test_height_axis_span_is_thickness():
    unit = Unit(t_pos=10, b_pos=4)
    _thickness_from_positions(_column("height", unit))
    assert (unit.min_thick, unit.max_thick) == (6, 6)


def test_unset_axis_is_height():
    unit = Unit(t_pos=3, b_pos=0)
    _thickness_from_positions(_column(None, unit))
    assert unit.max_thick == 3


def test_age_axis_has_no_span():
    unit = Unit(t_pos=1, b_pos=2)
    _thickness_from_positions(_column("age", unit))
    assert (unit.min_thick, unit.max_thick) == (None, None)


def test_given_thickness_is_kept():
    unit = Unit(t_pos=10, b_pos=4, min_thick=100, max_thick=200)
    _thickness_from_positions(_column("height", unit))
    assert (unit.min_thick, unit.max_thick) == (100, 200)
