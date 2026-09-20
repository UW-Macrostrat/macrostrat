"""Legend color variants are chosen by place and size, not by chance."""

from macrostrat.map_integration.utils.legend_color import (
    LegendRow,
    assign_colors,
    color_key,
    color_variants,
    variant_index,
)


def row(legend_id, cx, cy, area_km, color="#ff8800", top=0.0, bottom=2.58):
    return LegendRow(legend_id, color, top, bottom, cx, cy, area_km)


def test_key_survives_small_geometry_changes():
    # A re-mapping that nudges the bounding box and trims some area keeps the key.
    assert color_key(-92.31, 38.12, 1500.0) == color_key(-92.29, 38.15, 1400.0)


def test_key_changes_across_a_cell_or_size_class():
    base = color_key(-92.31, 38.12, 1500.0)
    assert color_key(-91.9, 38.12, 1500.0) != base
    assert color_key(-92.31, 38.12, 3000.0) != base


def test_small_areas_share_one_size_class():
    assert color_key(0.1, 0.1, 0.2)[2] == color_key(0.1, 0.1, 0.9)[2] == 0


def test_variant_index_is_deterministic_and_in_range():
    key = color_key(-92.31, 38.12, 1500.0)
    assert variant_index(key, 21) == variant_index(key, 21)
    assert all(0 <= variant_index((i, i, i), 21) < 21 for i in range(200))


def test_variants_start_with_the_base_and_are_distinct():
    variants = color_variants("#ff8800")
    assert variants[0] == "#ff8800"
    assert len(variants) == 21
    assert len(set(variants)) == len(variants)


def test_color_depends_only_on_base_place_and_size():
    # The same unit alone in its age class, or beside another of the same age,
    # gets the same color either way.
    alone = assign_colors([row(1, -92.3, 38.1, 100.0)])
    crowded = assign_colors([row(1, -92.3, 38.1, 100.0), row(2, -91.0, 38.1, 100.0)])
    assert alone.get(1, "#ff8800") == crowded.get(1, "#ff8800")


def test_same_place_and_size_gets_the_same_color_under_a_different_id():
    # Two maps of the same unit, different legend ids, one relabelled: same color.
    sgmc = [row(1, -92.31, 38.12, 1500.0), row(2, -90.0, 40.0, 12.0)]
    ngs = [row(101, -92.29, 38.15, 1450.0), row(102, -90.0, 40.0, 12.0)]
    a, b = assign_colors(sgmc), assign_colors(ngs)
    assert a.get(1, "#ff8800") == b.get(101, "#ff8800")
    assert a.get(2, "#ff8800") == b.get(102, "#ff8800")


def test_rows_without_polygons_or_color_are_skipped():
    rows = [
        row(1, None, None, None),
        row(2, -92.3, 38.1, 100.0),
        row(3, -92.3, 38.1, 100.0, color=None),
    ]
    changes = assign_colors(rows)
    assert 1 not in changes and 3 not in changes


def test_unreadable_color_leaves_the_group_alone():
    rows = [
        row(1, -92.3, 38.1, 100.0, color="junk"),
        row(2, -91.0, 38.1, 100.0, color="junk"),
    ]
    assert assign_colors(rows) == {}
