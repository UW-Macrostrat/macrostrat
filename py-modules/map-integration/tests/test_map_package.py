"""Round trips through a Macrostrat map package, between two databases."""

import sqlite3
from pathlib import Path

import pytest

from macrostrat.database import Database
from macrostrat.database.utils import template_database
from macrostrat.map_integration.commands.ingest import _map_packages
from macrostrat.map_integration.package import (
    ConflictAction,
    ImportStopped,
    compilation_tree,
    export_maps,
    format,
    import_package,
    is_map_package,
    read_package,
)
from macrostrat.map_integration.package.patch import apply_patch, plan_patch
from macrostrat.map_integration.source_tables import create_source_tables
from macrostrat.map_integration.utils.map_info import get_map_info, resolve_maps

SEED = """
INSERT INTO maps.sources (slug, name, scale, primary_table, keywords) VALUES
  ('pkg-a', 'Map A', 'large', 'pkg-a_polygons', ARRAY['one', 'two']),
  ('pkg-b', 'Map B', 'large', NULL, NULL),
  ('pkg-comp', 'Compilation', 'large', NULL, NULL),
  ('pkg-other', 'Not exported', 'large', NULL, NULL);
UPDATE maps.sources SET superseded_by = map_bounds.source_id('pkg-a')
  WHERE slug = 'pkg-b';

INSERT INTO maps.polygons (source_id, scale, orig_id, name, lith, geom)
SELECT map_bounds.source_id(slug), 'large', '1', slug || ' unit', 'sandstone',
       ST_MakeEnvelope(x, 0, x + 1, 1, 4326)
FROM (VALUES ('pkg-a', 0), ('pkg-a', 1), ('pkg-b', 3)) v(slug, x);

INSERT INTO maps.lines (source_id, scale, name, type, geom) VALUES
  (map_bounds.source_id('pkg-a'), 'large', 'fault', 'fault',
   ST_MakeLine(ST_Point(0, 0, 4326), ST_Point(1, 1, 4326)));
INSERT INTO maps.points (source_id, point_type, strike, dip, geom) VALUES
  (map_bounds.source_id('pkg-a'), 'bedding', 45, 10, ST_Point(0.5, 0.5, 4326));

INSERT INTO maps.legend (source_id, name, lith, lith_ids, best_age_top, color)
SELECT source_id, slug || ' unit', 'sandstone', ARRAY[1, 2], 12.345, '#ff0000'
FROM maps.sources WHERE slug IN ('pkg-a', 'pkg-b');
INSERT INTO maps.map_legend (legend_id, map_id)
SELECT l.legend_id, p.map_id FROM maps.polygons p
JOIN maps.legend l USING (source_id);

-- A materialized compilation: its polygon names a member's in `orig_id`
INSERT INTO maps.polygons (source_id, scale, orig_id, name, geom)
SELECT map_bounds.source_id('pkg-comp'), 'large', map_id::text, name, geom
FROM maps.polygons WHERE source_id = map_bounds.source_id('pkg-b');
INSERT INTO maps.map_legend (legend_id, map_id)
SELECT ml.legend_id, c.map_id FROM maps.polygons c
JOIN maps.map_legend ml ON ml.map_id = c.orig_id::integer
WHERE c.source_id = map_bounds.source_id('pkg-comp');

INSERT INTO maps_metadata.ingest_process (source_id, slug, state, comments, polygon_state)
VALUES (map_bounds.source_id('pkg-a'), 'pkg-a', 'ingested', 'fine', '{"status": "ingested"}');
INSERT INTO maps_metadata.ingest_process_tag (source_id, tag)
VALUES (map_bounds.source_id('pkg-a'), 'test');

INSERT INTO map_bounds.compilation (source_id, assembly_mode, note)
VALUES (map_bounds.source_id('pkg-comp'), 'mosaic', 'a note');
INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
SELECT map_bounds.source_id('pkg-comp'), map_bounds.source_id(m), p
FROM (VALUES ('pkg-a', 1), ('pkg-b', 2)) v(m, p);
-- A placement in a seeded layer, which travels by slug
INSERT INTO map_bounds.compilation_member (compilation_id, member_id)
VALUES (map_bounds.source_id('large'), map_bounds.source_id('pkg-a'));

INSERT INTO map_bounds.map_area (id, geometry, map_layer)
SELECT map_bounds.source_id(slug), ST_Multi(ST_MakeEnvelope(x, 0, x + 2, 1, 4326)),
       map_bounds.barrier_layer()
FROM (VALUES ('pkg-a', 0), ('pkg-b', 3), ('pkg-comp', 0)) v(slug, x);
INSERT INTO map_bounds.boundary_op (source_id, position, operation, parameters)
VALUES (map_bounds.source_id('pkg-a'), 0, 'union', '{}'),
       (map_bounds.source_id('pkg-a'), 1, 'simplify', '{"tolerance": 0.01}');
"""


@pytest.fixture(scope="module")
def base_db(schema_harness):
    """The full schema, without the reference data these tests don't need."""
    db = schema_harness.load_schema()
    db.session.close()
    db.engine.dispose()
    return db


@pytest.fixture(scope="module")
def source_db(base_db):
    with template_database(base_db.engine.url, close_source_connections=True) as engine:
        db = Database(engine)
        db.run_sql(SEED, raise_errors=True)
        for slug in ("pkg-a", "pkg"):
            create_source_tables(db, slug, kinds=("polygons",))
        db.run_sql(
            """
            INSERT INTO sources."pkg-a_polygons" (source_id, name, geom)
            VALUES (map_bounds.source_id('pkg-a'), 'staged', ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326))),
                   -- Appended since `prepare-fields`: still the owner's
                   (NULL, 'unassigned', NULL);
            -- A table shared by several maps, one of them not exported
            INSERT INTO sources.pkg_polygons (source_id, name, geom)
            SELECT map_bounds.source_id(s), s, ST_Multi(ST_MakeEnvelope(0, 0, 1, 1, 4326))
            FROM unnest(ARRAY['pkg-a', 'pkg-b', 'pkg-other']) s;
            """,
            raise_errors=True,
        )
        db.session.commit()
        yield db
        db.engine.dispose()


def export_compilation(db, path: Path) -> Path:
    root = get_map_info(db, "pkg-comp")
    maps = resolve_maps(db, [str(i) for i in compilation_tree(db, root)])
    export_maps(
        db,
        path,
        maps,
        staging_prefixes={"pkg"},
        metadata={"exported_from": "test"},
    )
    return path


@pytest.fixture(scope="module")
def package(source_db, tmp_path_factory) -> Path:
    return export_compilation(
        source_db, tmp_path_factory.mktemp("package") / "pkg.gpkg"
    )


@pytest.fixture
def target_db(base_db):
    """An empty target whose sequences have moved on, so every id must be remapped."""
    with template_database(base_db.engine.url, close_source_connections=True) as engine:
        db = Database(engine)
        db.run_sql(
            """
            SELECT setval('maps.sources_source_id_seq', 5000);
            SELECT setval('maps.map_ids', 5000);
            SELECT setval('maps.legend_legend_id_seq', 5000);
            SELECT setval('maps.line_ids', 5000);
            """,
            raise_errors=True,
        )
        yield db
        db.engine.dispose()


def scalar(db, sql, **params):
    return db.run_query(sql, params).scalar()


def test_package_contents(package):
    assert is_map_package(package)
    pkg = read_package(package)
    slugs = {r["slug"] for r in pkg.all_rows("maps_sources")}
    # The compilation's tree, without the map outside it
    assert slugs == {"pkg-a", "pkg-b", "pkg-comp"}
    assert pkg.layers["polygons"].row_count == 4
    assert pkg.layers["boundary_op"].row_count == 2
    # A shared staging table contributes only the exported maps' rows
    assert pkg.layers["sources__pkg_polygons"].row_count == 2
    assert pkg.layers["sources__pkg_polygons"].owner is None
    assert pkg.layers["sources__pkg-a_polygons"].owner == "pkg-a"
    # Derived topology state stays behind
    assert pkg.layers["map_area"].column("topo") is None


def test_chunked_export(source_db, package, tmp_path, monkeypatch):
    """Writing a layer in many pieces changes nothing about its contents."""
    monkeypatch.setattr(format, "FETCH_SIZE", 1)
    monkeypatch.setattr(format, "CHUNK_BYTES", 1)
    chunked = read_package(export_compilation(source_db, tmp_path / "chunked.gpkg"))
    whole = read_package(package)
    assert chunked.layers.keys() == whole.layers.keys()
    for name in whole.layers:
        assert chunked.all_rows(name) == whole.all_rows(name), name


def test_not_a_package(tmp_path):
    other = tmp_path / "plain.gpkg"
    other.write_bytes(b"not a geopackage")
    assert not is_map_package(other)
    assert not is_map_package(tmp_path / "missing.gpkg")
    assert _map_packages("some-slug", [other]) == (None, None)


def test_ingest_branch(package):
    assert _map_packages(str(package), []) == ([package], None)
    assert _map_packages("pkg-a", [package]) == ([package], ["pkg-a"])


def test_import(target_db, package):
    db = target_db
    report = import_package(db, package)
    assert set(report.imported) == {"pkg-a", "pkg-b", "pkg-comp"}
    assert report.warnings == []

    a = get_map_info(db, "pkg-a").id
    assert a > 5000
    assert scalar(
        db, "SELECT keywords FROM maps.sources WHERE source_id = :a", a=a
    ) == ["one", "two"]
    assert (
        scalar(
            db,
            "SELECT s.slug FROM maps.sources b JOIN maps.sources s ON s.source_id = b.superseded_by"
            " WHERE b.slug = 'pkg-b'",
        )
        == "pkg-a"
    )

    counts = db.run_query(
        """SELECT s.slug,
          (SELECT count(*) FROM maps.polygons p WHERE p.source_id = s.source_id) polygons,
          (SELECT count(*) FROM maps.lines l WHERE l.source_id = s.source_id) lines,
          (SELECT count(*) FROM maps.points t WHERE t.source_id = s.source_id) points
        FROM maps.sources s WHERE s.slug LIKE 'pkg-%' ORDER BY slug"""
    ).all()
    assert [tuple(r) for r in counts] == [
        ("pkg-a", 2, 1, 1),
        ("pkg-b", 1, 0, 0),
        ("pkg-comp", 1, 0, 0),
    ]

    # Every legend link joins a polygon to a legend under new ids: members to
    # their own, the compilation's polygon to its member's
    links = db.run_query(
        """SELECT ps.slug polygon, ls.slug legend, l.best_age_top, l.lith_ids
        FROM maps.map_legend ml
        JOIN maps.polygons p USING (map_id) JOIN maps.legend l USING (legend_id)
        JOIN maps.sources ps ON ps.source_id = p.source_id
        JOIN maps.sources ls ON ls.source_id = l.source_id
        ORDER BY 1"""
    ).all()
    assert [(r.polygon, r.legend) for r in links] == [
        ("pkg-a", "pkg-a"),
        ("pkg-a", "pkg-a"),
        ("pkg-b", "pkg-b"),
        ("pkg-comp", "pkg-b"),
    ]
    assert float(links[0].best_age_top) == 12.345 and links[0].lith_ids == [1, 2]
    assert (
        scalar(
            db,
            """SELECT count(*) FROM maps.polygons c JOIN maps.polygons m
        ON m.map_id = c.orig_id::integer AND m.source_id = map_bounds.source_id('pkg-b')
        WHERE c.source_id = map_bounds.source_id('pkg-comp')""",
        )
        == 1
    )

    edges = db.run_query(
        """SELECT c.slug, m.slug, cm.priority FROM map_bounds.compilation_member cm
        JOIN maps.sources c ON c.source_id = cm.compilation_id
        JOIN maps.sources m ON m.source_id = cm.member_id ORDER BY 1, 2"""
    ).all()
    edges = [tuple(e) for e in edges if e[1].startswith("pkg-")]
    assert edges == [
        ("large", "pkg-a", None),
        ("pkg-comp", "pkg-a", 1),
        ("pkg-comp", "pkg-b", 2),
    ]
    assert (
        scalar(
            db,
            "SELECT assembly_mode FROM map_bounds.compilation"
            " WHERE source_id = map_bounds.source_id('pkg-comp')",
        )
        == "mosaic"
    )

    # The boundary is recorded in the target's own barrier layer
    area = db.run_query(
        "SELECT a.map_layer = map_bounds.barrier_layer() AS in_barrier, geometry_hash"
        " FROM map_bounds.map_area a WHERE a.id = :a",
        dict(a=a),
    ).one()
    assert area.in_barrier and area.geometry_hash is None
    ops = db.run_query(
        "SELECT operation, parameters FROM map_bounds.boundary_op WHERE source_id = :a"
        " ORDER BY position",
        dict(a=a),
    ).all()
    assert [(o.operation, o.parameters) for o in ops] == [
        ("union", {}),
        ("simplify", {"tolerance": 0.01}),
    ]

    process = db.run_query(
        "SELECT state, polygon_state FROM maps_metadata.ingest_process WHERE source_id = :a",
        dict(a=a),
    ).one()
    assert process.state == "ingested" and process.polygon_state == {
        "status": "ingested"
    }
    assert (
        scalar(
            db,
            "SELECT tag FROM maps_metadata.ingest_process_tag WHERE source_id = :a",
            a=a,
        )
        == "test"
    )

    # Staging tables come back with the target's source ids
    staged = (
        db.run_query(
            "SELECT s.slug FROM sources.pkg_polygons p JOIN maps.sources s USING (source_id) ORDER BY 1"
        )
        .scalars()
        .all()
    )
    assert staged == ["pkg-a", "pkg-b"]
    assert db.run_query(
        'SELECT source_id FROM sources."pkg-a_polygons" ORDER BY _pkid'
    ).scalars().all() == [a, None]
    # ... and stay usable
    db.run_sql("INSERT INTO sources.\"pkg-a_polygons\" (name) VALUES ('more')")

    assert (
        scalar(
            db,
            "SELECT details->>'exported_from' FROM maps.source_operations WHERE source_id = :a",
            a=a,
        )
        == "test"
    )


def _snapshot(db):
    return db.run_query(
        """SELECT s.slug, s.source_id,
          (SELECT array_agg(map_id ORDER BY map_id) FROM maps.polygons p WHERE p.source_id = s.source_id)
        FROM maps.sources s WHERE slug LIKE 'pkg-%' ORDER BY slug"""
    ).all()


def test_conflicts(target_db, package):
    db = target_db
    import_package(db, package)
    before = _snapshot(db)

    with pytest.raises(ImportStopped):
        import_package(db, package)  # `ask`, with nobody to ask
    with pytest.raises(ImportStopped):
        import_package(db, package, on_conflict=ConflictAction.stop)
    report = import_package(db, package, on_conflict=ConflictAction.skip)
    assert sorted(report.skipped) == ["pkg-a", "pkg-b", "pkg-comp"]
    assert _snapshot(db) == before

    # The resolver is asked once per slug; answers apply independently
    asked = []

    def resolve(slug):
        asked.append(slug)
        return ConflictAction.overwrite if slug == "pkg-a" else ConflictAction.skip

    report = import_package(db, package, resolve=resolve)
    assert sorted(asked) == ["pkg-a", "pkg-b", "pkg-comp"]
    assert report.overwritten == ["pkg-a"]

    after = _snapshot(db)
    # Same source ids, same feature counts, fresh polygon ids for the overwritten map
    assert [(r[0], r[1], len(r[2])) for r in after] == [
        (r[0], r[1], len(r[2])) for r in before
    ]
    assert after[0][2] != before[0][2] and after[1:] == before[1:]
    assert (
        scalar(
            db, "SELECT count(*) FROM maps.legend WHERE source_id = :a", a=before[0][1]
        )
        == 1
    )
    assert (
        scalar(
            db,
            "SELECT count(*) FROM map_bounds.boundary_op WHERE source_id = :a",
            a=before[0][1],
        )
        == 2
    )
    # Shared staging rows were replaced, not duplicated
    assert scalar(db, "SELECT count(*) FROM sources.pkg_polygons") == 2


def test_only(target_db, package):
    report = import_package(target_db, package, only=["pkg-a"])
    assert set(report.imported) == {"pkg-a"}
    # An edge to a map left behind can't be made, and says so; the other maps'
    # own rows are left out without comment
    assert report.warnings == [
        "compilation_member: 1 edges name a map not in the target"
    ]
    assert scalar(target_db, "SELECT count(*) FROM sources.pkg_polygons") == 1


def test_resilient_to_stale_information(target_db, package, tmp_path):
    """Ingest state the target doesn't know, and a column it doesn't have."""
    stale = tmp_path / "stale.gpkg"
    stale.write_bytes(package.read_bytes())
    with sqlite3.connect(stale) as pkg:
        pkg.execute("UPDATE ingest_process SET state = 'retired-state'")
        pkg.execute("ALTER TABLE legend ADD COLUMN future_column TEXT")
        pkg.execute(
            "INSERT INTO macrostrat_package_columns VALUES"
            " ('legend', 999, 'future_column', 'text', 'text')"
        )

        # A compilation edge that can't be made: members may not cycle
        pkg.execute(
            "INSERT INTO compilation_member (compilation_id, member_id, priority,"
            " compilation_slug, member_slug) VALUES (0, 0, NULL, 'pkg-a', 'pkg-comp')"
        )
        pkg.execute(
            "UPDATE macrostrat_package_layers SET row_count = row_count + 1"
            " WHERE layer = 'compilation_member'"
        )

    report = import_package(target_db, stale)
    assert set(report.imported) == {"pkg-a", "pkg-b", "pkg-comp"}
    assert any("retired-state" in w for w in report.warnings)
    assert any("future_column" in w for w in report.warnings)
    assert any(
        w.startswith("compilation_member: skipped 1 of 4") for w in report.warnings
    )
    # The process is kept without its state, so its tag has somewhere to go
    process = target_db.run_query(
        "SELECT state, comments FROM maps_metadata.ingest_process"
    ).one()
    assert tuple(process) == (None, "fine")
    assert (
        scalar(target_db, "SELECT count(*) FROM maps_metadata.ingest_process_tag") == 1
    )
    # ... and the rest of the map is whole
    assert scalar(target_db, "SELECT count(*) FROM maps.legend") == 2
    assert (
        scalar(
            target_db,
            "SELECT count(*) FROM map_bounds.compilation_member"
            " WHERE compilation_id = map_bounds.source_id('pkg-comp')",
        )
        == 2
    )


@pytest.fixture(scope="module")
def ops_package(source_db, tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("partial") / "ops.gpkg"
    maps = resolve_maps(source_db, ["pkg-a", "pkg-b"])
    export_maps(source_db, path, maps, elements=["boundary-ops"])
    return path


def test_partial_package(ops_package, target_db):
    pkg = read_package(ops_package)
    assert pkg.elements == ["boundary-ops"]
    assert pkg.format_version == 2
    assert set(pkg.layers) == {"maps_sources", "boundary_op"}
    # A package of parts can't stand in for whole maps
    with pytest.raises(ImportStopped, match="holds only boundary-ops"):
        import_package(target_db, ops_package)


def _ops(db, slug):
    rows = db.run_query(
        "SELECT operation, parameters, geometry IS NOT NULL AS g"
        " FROM map_bounds.boundary_op WHERE source_id = map_bounds.source_id(:s)"
        " ORDER BY position",
        dict(s=slug),
    ).all()
    return [tuple(r) for r in rows]


def test_patch(target_db, package):
    db = target_db
    import_package(db, package)
    # The target has diverged since: edited metadata and a different stack,
    # with a union cached from its own features
    db.run_sql(
        """
        UPDATE maps.sources SET name = 'Renamed here' WHERE slug = 'pkg-a';
        UPDATE maps.sources SET url = 'https://kept.example' WHERE slug = 'pkg-b';
        DELETE FROM map_bounds.boundary_op
          WHERE source_id = map_bounds.source_id('pkg-a') AND position = 1;
        INSERT INTO map_bounds.boundary_op (source_id, position, operation, parameters)
          VALUES (map_bounds.source_id('pkg-a'), 1, 'buffer', '{"distance": 1}');
        UPDATE map_bounds.boundary_op SET geometry = ST_Multi(ST_MakeEnvelope(0, 0, 9, 9, 4326))
          WHERE source_id = map_bounds.source_id('pkg-a') AND position = 0;
        """,
        raise_errors=True,
    )
    db.session.commit()

    plan = plan_patch(db, package)
    assert [(c.slug, c.element) for c in plan.changes] == [
        ("pkg-a", "metadata"),
        ("pkg-a", "boundary-ops"),
    ]
    assert list(plan.changes[0].data) == ["name"]
    # The package has no url for pkg-b, which doesn't clear the target's
    assert plan.unchanged == ["pkg-b", "pkg-comp"]
    assert plan.missing == [] and plan.warnings == []

    narrowed = plan_patch(db, package, elements=["boundary-ops"], only=["pkg-a"])
    assert [c.element for c in narrowed.changes] == ["boundary-ops"]

    apply_patch(db, plan)
    assert scalar(db, "SELECT name FROM maps.sources WHERE slug = 'pkg-a'") == "Map A"
    assert (
        scalar(db, "SELECT url FROM maps.sources WHERE slug = 'pkg-b'")
        == "https://kept.example"
    )
    # The opening is unchanged, so the target's own cache stands
    assert _ops(db, "pkg-a") == [
        ("union", {}, True),
        ("simplify", {"tolerance": 0.01}, False),
    ]
    assert (
        scalar(
            db,
            "SELECT count(*) FROM maps.source_operations"
            " WHERE operation = 'patch-package' AND source_id = map_bounds.source_id('pkg-a')",
        )
        == 1
    )
    # Applying again changes nothing
    assert plan_patch(db, package).changes == []


def test_patch_partial(target_db, package, ops_package):
    db = target_db
    import_package(db, package, only=["pkg-a"])
    db.run_sql(
        """
        DELETE FROM map_bounds.boundary_op WHERE source_id = map_bounds.source_id('pkg-a');
        UPDATE maps.sources SET name = 'Renamed here' WHERE slug = 'pkg-a';
        """,
        raise_errors=True,
    )
    db.session.commit()

    with pytest.raises(Exception, match="doesn't carry metadata"):
        plan_patch(db, ops_package, elements=["metadata"])
    plan = plan_patch(db, ops_package)
    # Only the element the package was exported with, and never a new map
    assert [(c.slug, c.element) for c in plan.changes] == [("pkg-a", "boundary-ops")]
    assert plan.changes[0].summary == "replace stack: 0 → 2 ops"
    assert plan.missing == ["pkg-b"]
    apply_patch(db, plan)
    assert [o[0] for o in _ops(db, "pkg-a")] == ["union", "simplify"]
    assert scalar(db, "SELECT name FROM maps.sources WHERE slug = 'pkg-a'") == (
        "Renamed here"
    )
    assert scalar(db, "SELECT count(*) FROM maps.sources WHERE slug = 'pkg-b'") == 0
