"""Tests for column writing: multiple sections per column, and geometry."""

from macrostrat.column_ingestion.columns import (
    GeometryError,
    group_units_by_section,
    resolve_geometry,
    section_bounds,
)
from macrostrat.column_ingestion.columns.geometry import POINT_AREA_KM2
from macrostrat.column_ingestion.ingest import ingest_columns_from_file
from macrostrat.column_ingestion.intervals import (
    UNMODELED_INTERVAL,
    Interval,
    RelativeAge,
)
from macrostrat.column_ingestion.units import Unit

SQUARE = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"


def interval(id, name, age_bottom, age_top):
    return Interval(id, name, age_bottom, age_top, 5, "epoch")


def unit(section_key, *, b=None, t=None):
    u = Unit(section_key=section_key, b_pos=10.0, t_pos=0.0)
    if b is not None:
        u.b_age = RelativeAge(b, 0)
    if t is not None:
        u.t_age = RelativeAge(t, 1)
    return u


# --- sections: grouping and bounds, no database needed -----------------------------


def test_units_group_into_sections_in_label_order():
    units = [unit(3), unit(1), unit(2), unit(1)]

    groups = group_units_by_section(units)

    assert list(groups) == [1, 2, 3]
    assert len(groups[1]) == 2


def test_section_labels_sort_numerically_not_textually():
    """'10' must come after '9', which string ordering would get wrong."""
    groups = group_units_by_section([unit("10"), unit("9"), unit("2")])

    assert list(groups) == ["2", "9", "10"]


def test_section_bounds_take_the_oldest_bottom_and_youngest_top():
    """`fo` is the interval with the greatest age_bottom among the section's units,
    `lo` the one with the least age_top — the rule the legacy importer established."""
    old = interval(1, "Cambrian", 538.8, 486.85)
    young = interval(2, "Ordovician", 486.85, 443.1)

    fo, lo = section_bounds([unit(1, b=old, t=old), unit(1, b=young, t=young)])

    assert fo == old.id, "oldest bottom interval"
    assert lo == young.id, "youngest top interval"


def test_section_bounds_fall_back_to_the_unmodeled_sentinel():
    """A section whose units carry no intervals is unconstrained, not an error."""
    assert section_bounds([unit(1), unit(1)]) == (
        UNMODELED_INTERVAL,
        UNMODELED_INTERVAL,
    )


def test_section_bounds_ignore_units_missing_one_side():
    old = interval(1, "Cambrian", 538.8, 486.85)

    fo, lo = section_bounds([unit(1, b=old, t=old), unit(1)])

    assert (fo, lo) == (old.id, old.id)


# --- geometry: needs PostGIS, so it needs a database ------------------------------


class TestGeometry:
    def test_point_geometry(self, db):
        geom = resolve_geometry(db, lat=43.07, lng=-89.4)

        assert (geom.lat, geom.lng) == (43.07, -89.4)
        assert geom.area_km2 == POINT_AREA_KM2, "a point has no footprint"
        assert geom.poly_geom is None and geom.wkt is None

    def test_polygon_derives_point_and_geodesic_area(self, db):
        geom = resolve_geometry(db, geom=SQUARE)

        assert (geom.lat, geom.lng) == (
            0.5,
            0.5,
        ), "point-on-surface, inside the polygon"
        assert geom.area_km2 > 12_000, "geodesic km^2, not degrees"
        assert geom.poly_geom is not None
        assert geom.wkt == SQUARE

    def test_polygon_wins_over_a_supplied_point(self, db):
        geom = resolve_geometry(db, lat=80.0, lng=80.0, geom=SQUARE)

        assert (geom.lat, geom.lng) == (0.5, 0.5)

    def test_missing_geometry_is_an_error(self, db):
        try:
            resolve_geometry(db, label="column 7")
        except GeometryError as err:
            assert "column 7" in str(err)
        else:
            raise AssertionError("expected GeometryError")

    def test_non_polygon_geometry_is_rejected(self, db):
        try:
            resolve_geometry(db, geom="LINESTRING(0 0, 1 1)")
        except GeometryError as err:
            assert "POLYGON" in str(err)
        else:
            raise AssertionError("expected GeometryError")

    def test_invalid_polygon_is_rejected(self, db):
        # A bowtie: self-intersecting, so ST_IsValid is false.
        try:
            resolve_geometry(db, geom="POLYGON((0 0, 1 1, 1 0, 0 1, 0 0))")
        except GeometryError as err:
            assert "invalid geometry" in str(err)
        else:
            raise AssertionError("expected GeometryError")


# --- the whole path, against the fixture workbook --------------------------------


class TestIngestedColumns:
    def test_multiple_sections_per_column(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        """The workbook has two columns: 9999 with sections 1/2/3 and 2215 with section 1.

        Sections used to be a stub — one per column, with `fo = lo = -1` sentinels. Note
        both columns label a section "1", so this also pins that section labels are scoped
        per column rather than globally.
        """
        ingest_columns_from_file(db, excel_file)

        rows = db.run_query(
            """
            SELECT s.id, s.col_id, s.fo, s.lo, count(u.id) n_units
            FROM macrostrat.sections s
            LEFT JOIN macrostrat.units u ON u.section_id = s.id
            GROUP BY s.id, s.col_id, s.fo, s.lo ORDER BY s.id
            """
        ).fetchall()

        per_column = {}
        for row in rows:
            per_column.setdefault(row.col_id, []).append(row)

        assert sorted(len(v) for v in per_column.values()) == [1, 3]
        assert sum(r.n_units for r in rows) == 6
        assert all(r.n_units > 0 for r in rows), "no orphan sections"
        assert all(r.fo > 0 and r.lo > 0 for r in rows), "no -1 sentinels"

    def test_units_reference_their_own_section(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        """The `units_sections_fk` foreign key holds, which is what lets the schema keep
        it — sections are created before the units that point at them."""
        ingest_columns_from_file(db, excel_file)

        orphaned = db.run_query(
            """
            SELECT count(*) FROM macrostrat.units u
            LEFT JOIN macrostrat.sections s ON s.id = u.section_id
            WHERE s.id IS NULL
            """
        ).scalar()
        assert orphaned == 0

    def test_column_geometry_is_written(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        """The workbook's first column supplies lat/lng; the rest supply polygons."""
        ingest_columns_from_file(db, excel_file)

        rows = db.run_query(
            """
            SELECT col_name, lat, lng, col_area, poly_geom IS NOT NULL AS has_poly
            FROM macrostrat.cols ORDER BY id
            """
        ).fetchall()
        assert rows, "columns were written"

        # No placeholder zeros: every column has a real location.
        assert all(r.lat != 0 or r.lng != 0 for r in rows)
        polygons = [r for r in rows if r.has_poly]
        assert polygons, "the workbook has polygon columns"
        assert all(r.col_area > 0 for r in polygons), "polygons get a geodesic area"
