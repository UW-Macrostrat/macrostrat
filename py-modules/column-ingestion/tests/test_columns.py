"""Tests for column writing: sections, identified and derived, and geometry."""

from pytest import raises

from macrostrat.column_ingestion.columns import (
    Column,
    GeometryError,
    Section,
    ordered_sections,
    resolve_geometry,
    section_bounds,
    section_identity,
    single_section,
    split_at_gaps,
)
from macrostrat.column_ingestion.columns.geometry import POINT_AREA_KM2
from macrostrat.column_ingestion.database import ProjectIdentifier
from macrostrat.column_ingestion.ingest import ingest_columns, ingest_columns_from_file
from macrostrat.column_ingestion.intervals import (
    UNMODELED_INTERVAL,
    Interval,
    RelativeAge,
)
from macrostrat.column_ingestion.units import BoundaryType, Unit

SQUARE = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"


def interval(id, name, age_bottom, age_top):
    return Interval(id, name, age_bottom, age_top, 5, "epoch")


def unit(*, b=None, t=None, orig_id=None, pos=(10.0, 0.0)):
    u = Unit(b_pos=pos[0], t_pos=pos[1], orig_id=orig_id)
    if b is not None:
        u.b_age = RelativeAge(b, 0)
    if t is not None:
        u.t_age = RelativeAge(t, 1)
    return u


# --- sections: identity, derivation and order, no database needed --------------------


def test_a_blank_identifier_is_no_identifier():
    """A CSV-sourced pipeline yields `''` rather than NULL, and an empty string is not an
    identity — treated as one, every unidentified section would collapse onto one key."""
    assert Section(orig_id="  ").orig_id is None
    assert Section(orig_id=" S-1 ").orig_id == "S-1"
    assert Section(orig_id=1).orig_id == "1", "a workbook label is an identifier too"


def test_identified_sections_key_on_their_identifier_and_the_rest_on_the_column():
    identified = section_identity({"col_id": 7, "orig_id": "S-1"})
    renamed = section_identity({"col_id": 7, "orig_id": "S-2"})
    unidentified = section_identity({"col_id": 7, "orig_id": None})
    blank = section_identity({"col_id": 7, "orig_id": ""})

    assert identified != renamed, "the identifier is the identity"
    assert unidentified == blank == ("ordinal", 7), "no identifier: positional"
    assert identified != unidentified, "the two kinds never pair against each other"


def test_single_section_is_one_unidentified_package():
    a, b = unit(pos=(0, 10)), unit(pos=(10, 20))

    (section,) = single_section([a, b])

    assert section.orig_id is None and section.units == [a, b]
    assert single_section([]) == []


def test_split_at_gaps_opens_a_section_at_a_non_conformable_base():
    """The rule GBDB and ChinaLex each derived on their own, now owned here. The lowest
    unit's own basal unconformity opens nothing — there is no section below it."""
    basement_top = unit(pos=(0, 10))
    basement_top.b_surface_type = BoundaryType.UNCONFORMITY
    conformable = unit(pos=(10, 20))
    conformable.b_surface_type = BoundaryType.CONFORMITY
    above_unconformity = unit(pos=(20, 30))
    above_unconformity.b_surface_type = BoundaryType.UNCONFORMITY
    faulted = unit(pos=(30, 40))
    faulted.b_surface_type = BoundaryType.FAULT

    sections = split_at_gaps([faulted, basement_top, above_unconformity, conformable])

    assert [s.units for s in sections] == [
        [basement_top, conformable],
        [above_unconformity],
        [faulted],
    ], "from the base upward, regardless of input order"
    assert all(s.orig_id is None for s in sections)


def test_split_at_gaps_opens_a_section_where_the_position_chain_breaks():
    """Missing rock is a gap whether or not the source labelled the contact."""
    lower, upper = unit(pos=(0, 10)), unit(pos=(15, 20))
    touching = unit(pos=(20, 30))

    sections = split_at_gaps([lower, upper, touching])

    assert [s.units for s in sections] == [[lower], [upper, touching]]


def test_split_at_gaps_reads_a_depth_column_from_the_base_up():
    """Positions increasing downward: the base is the largest position, and the chain
    is contiguous when a unit's base meets the top of the one below it."""
    deepest, middle, shallow = unit(pos=(30, 20)), unit(pos=(20, 10)), unit(pos=(10, 0))

    sections = split_at_gaps([shallow, deepest, middle])

    assert [s.units for s in sections] == [[deepest, middle, shallow]]


def test_split_at_gaps_leaves_unpositioned_units_in_the_topmost_section():
    floating = unit(pos=(None, None))
    lower, upper = unit(pos=(0, 10)), unit(pos=(15, 20))

    sections = split_at_gaps([floating, lower, upper])

    assert [s.units for s in sections] == [[lower], [upper, floating]]


def test_an_unconformity_inside_a_section_is_warned_about(caplog):
    """Placeholder handling: a section is a conformable package, so this is reported,
    not fixed. The lowest unit's own basal unconformity is the section's base and is
    not internal."""
    base, above = unit(pos=(0, 10)), unit(pos=(10, 20))
    base.b_surface_type = BoundaryType.UNCONFORMITY
    above.b_surface_type = BoundaryType.DISCONFORMITY

    with caplog.at_level("WARNING"):
        Section(orig_id="ok", units=[base])
    assert not caplog.records

    with caplog.at_level("WARNING"):
        Section(orig_id="split-me", units=[above, base])
    assert len(caplog.records) == 1 and "split-me" in caplog.text
    assert "split_at_gaps" in caplog.text

    with caplog.at_level("WARNING"):
        caplog.clear()
        split_at_gaps([above, base])
    assert not caplog.records, "the split is how you avoid the warning"


def test_sections_are_ordered_from_the_base_by_their_units_not_by_label():
    """For an unidentified section this order *is* its identity, so it has to come from
    the rock; a label would let two runs disagree about the same stack."""
    low = Section(orig_id="z", units=[unit(pos=(0, 10))])
    mid = Section(units=[unit(pos=(10, 20))])
    high = Section(orig_id="a", units=[unit(pos=(20, 30))])

    assert ordered_sections([high, mid, low]) == [low, mid, high]


def test_identified_and_unidentified_sections_share_a_column():
    """No regime: the key function keeps the two kinds in separate groups, so a column may
    ingest the sections its source names and derive the rest."""
    mixed = [
        Section(orig_id="S-1", units=[unit(pos=(0, 10))]),
        Section(units=[unit(pos=(10, 20))]),
    ]

    assert [s.orig_id for s in ordered_sections(mixed)] == ["S-1", None]


def test_sections_sharing_an_identifier_are_rejected():
    with raises(ValueError, match="share an identifier"):
        ordered_sections([Section(orig_id="S-1"), Section(orig_id="S-1")])


def test_assigning_units_to_a_column_makes_one_section():
    """The norm: a column is one section unless a pipeline says otherwise."""
    a, b = unit(pos=(0, 10)), unit(pos=(10, 20))
    column = Column()

    column.units = [a, b]

    assert len(column.sections) == 1 and column.sections[0].orig_id is None
    assert column.units == [a, b]


def test_a_column_flattens_its_sections_units_in_section_order():
    a, b, c = unit(), unit(), unit()
    column = Column(
        sections=[Section(orig_id=1, units=[a, b]), Section(orig_id=2, units=[c])]
    )

    assert column.units == [a, b, c]


def test_section_bounds_take_the_oldest_bottom_and_youngest_top():
    """`fo` is the interval with the greatest age_bottom among the section's units,
    `lo` the one with the least age_top — the rule the legacy importer established."""
    old = interval(1, "Cambrian", 538.8, 486.85)
    young = interval(2, "Ordovician", 486.85, 443.1)

    fo, lo = section_bounds([unit(b=old, t=old), unit(b=young, t=young)])

    assert fo == old.id, "oldest bottom interval"
    assert lo == young.id, "youngest top interval"


def test_section_bounds_fall_back_to_the_unmodeled_sentinel():
    """A section whose units carry no intervals is unconstrained, not an error."""
    assert section_bounds([unit(), unit()]) == (
        UNMODELED_INTERVAL,
        UNMODELED_INTERVAL,
    )


def test_section_bounds_ignore_units_missing_one_side():
    old = interval(1, "Cambrian", 538.8, 486.85)

    fo, lo = section_bounds([unit(b=old, t=old), unit()])

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


# --- ingested sections: the source divides the column ----------------------------


class TestIdentifiedSections:
    """Sections the source identifies — the shape ChinaLex and StraboSpot take — sharing
    a column with one it does not. No fixture workbook does this; the objects are built
    directly."""

    PROJECT = ProjectIdentifier(id=13)

    @staticmethod
    def _column(sections):
        return Column(
            local_id="1",
            orig_id="src-col-1",
            name="Source column",
            lat=43.07,
            lng=-89.4,
            sections=sections,
        )

    @staticmethod
    def _rows(db, table):
        return {
            r.orig_id: r.id
            for r in db.run_query(f"SELECT id, orig_id FROM {table} ORDER BY id")
        }

    def test_section_ids_survive_reordering_and_insertion(
        self, db, test_project, default_age_model_ref
    ):
        """The case ordinal identity cannot handle: a new section below the others would
        shift every unidentified section above it. An identified section is matched by
        its identifier, so it — and the units pinned to it — keep their ids; and the one
        unidentified section, alone in its ordinal group, keeps its id as well."""
        first = self._column(
            [
                Section(
                    orig_id="S-1",
                    units=[
                        unit(orig_id="1", pos=(0, 10)),
                        unit(orig_id="2", pos=(10, 20)),
                    ],
                ),
                Section(orig_id="S-2", units=[unit(orig_id="3", pos=(0, 5))]),
                Section(units=[unit(orig_id="9", pos=(50, 60))]),
            ]
        )
        ingest_columns(db, [first], project=self.PROJECT)
        sections = self._rows(db, "macrostrat.sections")
        units = self._rows(db, "macrostrat.units")
        assert set(sections) == {"S-1", "S-2", None}, (
            "identifiers are written to orig_id"
        )
        assert set(units) == {"1", "2", "3", "9"}

        second = self._column(
            [
                Section(orig_id="S-2", units=[unit(orig_id="3", pos=(0, 5))]),
                Section(orig_id="S-0", units=[unit(orig_id="4", pos=(0, 3))]),
                Section(units=[unit(orig_id="9", pos=(50, 60))]),
                Section(
                    orig_id="S-1",
                    units=[
                        unit(orig_id="1", pos=(0, 10)),
                        unit(orig_id="2", pos=(10, 20)),
                    ],
                ),
            ]
        )
        ingest_columns(db, [second], project=self.PROJECT)
        sections_after = self._rows(db, "macrostrat.sections")
        units_after = self._rows(db, "macrostrat.units")

        assert set(sections_after) == {"S-0", "S-1", "S-2", None}
        assert sections_after["S-1"] == sections["S-1"]
        assert sections_after["S-2"] == sections["S-2"]
        assert sections_after[None] == sections[None], "the derived one, ordinally"
        assert {k: units_after[k] for k in ("1", "2", "3", "9")} == units
        assert all(
            r.section_id == sections_after[r.section]
            for r in db.run_query(
                """
                SELECT u.section_id, s.orig_id AS section FROM macrostrat.units u
                JOIN macrostrat.sections s ON s.id = u.section_id
                """
            )
        ), "every unit references its own section"
