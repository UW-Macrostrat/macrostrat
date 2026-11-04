"""Same-age legends are told apart by variants chosen by place and size, not by chance."""

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
    assert len(variants) == 12
    assert len(set(variants)) == len(variants)


def test_a_unit_alone_in_its_age_keeps_the_interval_color():
    assert assign_colors([row(1, -92.3, 38.1, 100.0)]) == {}


def test_the_largest_of_a_group_keeps_the_base_and_the_rest_move():
    rows = [
        row(1, -92.3, 38.1, 5000.0),
        row(2, -91.0, 38.1, 100.0),
        row(3, -90.0, 37.0, 20.0),
    ]
    changes = assign_colors(rows)
    assert 1 not in changes
    assert set(changes) == {2, 3}
    assert all(c != "#ff8800" for c in changes.values())


def test_units_of_different_ages_are_not_grouped():
    rows = [row(1, -92.3, 38.1, 100.0), row(2, -91.0, 38.1, 100.0, bottom=5.33)]
    assert assign_colors(rows) == {}


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


def test_color_key_survives_float_noise_in_the_area():
    """A parallel `sum()` differs in its last bits; the key must not.

    `area_km` reaches this from `sum(ST_Area(...))`, and a parallel aggregate adds
    its workers' partial sums in whatever order they finish. That is invisible
    until an area lands near a power of two, where `floor(log2(...))` flips and a
    legend entry changes colour between two runs on identical input.
    """
    # 1024 km^2 exactly, and the same area as two different summation orders
    # might produce it.
    exact = 1024.0
    just_under = 1024.0 - 2e-10
    just_over = 1024.0 + 2e-10

    key = color_key(-105.0, 40.0, exact)
    assert color_key(-105.0, 40.0, just_under) == key
    assert color_key(-105.0, 40.0, just_over) == key

    # ...while a real difference in size still separates them.
    assert color_key(-105.0, 40.0, 2048.0) != key
    assert color_key(-105.0, 40.0, 512.0) != key


def test_color_key_still_separates_neighbours():
    """Rounding must not collapse the differentiation the key exists to provide."""
    base = color_key(-105.0, 40.0, 1000.0)
    # A different grid cell.
    assert color_key(-95.0, 40.0, 1000.0) != base
    assert color_key(-105.0, 30.0, 1000.0) != base


def _lch(hexcode):
    import spectra

    return spectra.html(hexcode).to("lch").values


def _hue_distance(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def test_pale_colors_keep_their_hue():
    """Desaturating past zero chroma used to turn Holocene cream blue."""
    for base in ("#FEF2E0", "#D9F1F7", "#CCD4C7"):
        _, _, hue = _lch(base)
        for v in color_variants(base):
            _, chroma, h = _lch(v)
            if chroma > 2:
                # Brightening near white clips a little hue; a flip is ~180 degrees.
                assert _hue_distance(h, hue) < 45, (base, v)


def test_grays_stay_gray():
    for base in ("#D6D6D6", "#A6A6A6", "#FFFFFF"):
        assert all(_lch(v)[1] < 2 for v in color_variants(base)), base


def test_saturated_colors_are_unchanged_by_the_hue_guard():
    # Chroma above 40 never reaches the guard: plain spectra moves.
    import spectra

    c = spectra.html("#ff8800")
    assert color_variants("#ff8800")[7:] == [
        c.saturate(amount=10).hexcode,
        c.desaturate(amount=10).hexcode,
        c.desaturate(amount=20).hexcode,
        c.saturate(amount=20).hexcode,
        c.saturate(amount=30).hexcode,
    ]
