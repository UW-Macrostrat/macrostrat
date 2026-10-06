from dataclasses import dataclass

from geoalchemy2.shape import from_shape
from mapboard.topology_manager import TopologyInspector, TopologyManager
from pytest import approx, fixture, mark, raises
from shapely.geometry import Point
from sqlalchemy.exc import DBAPIError

from macrostrat.map_topology import _set_dirty
from macrostrat.map_topology.config import create_topo_context
from macrostrat.map_topology.manager import (
    MacrostratTopologyManager,
    get_held_maps,
    get_map_list,
    get_retired_maps,
    proc,
    release_map,
    update_maps,
    vacuum_topology,
)


def geom(_shape, srid=4326):
    return str(from_shape(_shape, srid, extended=True))


@fixture(scope="class")
def ctx(test_db_base):
    yield create_topo_context(test_db_base)
    # These tests commit into the session-scoped database rather than a
    # rolled-back transaction, so the features they insert would otherwise leak
    # into later tests that expect `maps.polygons` to be empty.
    test_db_base.run_query(
        """
        DELETE FROM maps.polygons
        WHERE source_id IN (
          SELECT source_id FROM maps.sources WHERE starts_with(slug, 'test_source_')
        )
        """
    )
    test_db_base.session.commit()


class TestMapTopology:
    # def test_map_topology(self, ctx):
    #     # TODO: Need to work on test isolation here...
    #     create_topo_fixtures(ctx)

    def test_create_map_bounds(self, ctx):
        """Insert a few test maps into the database

        They have overlapping bounds so we can test the logic for merging them into
        a composite layer.
        """
        mgr = TopologyManager(ctx)
        db = mgr.database

        # Insert two non-overlapping test sources
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES
                (1001, 'test_source_1', true, 'active', 'large'),
                (1002, 'test_source_2', true, 'active', 'large');
            """
        )
        # A boundary is unioned from the map's own polygons, not read from
        # `rgeom` -- which is now a mirror of the boundary rather than a source
        # for it -- so a map without polygons never gets one.
        add_polygons(
            db,
            {
                1001: "ST_MakeEnvelope(0, 0, 2, 2, 4326)",
                1002: "ST_MakeEnvelope(3, 0, 5, 2, 4326)",
            },
        )

        update_maps(mgr, bulk=True)

        # Every piece marks the faces it touched dirty: the two maps' faces and
        # the universal face between them. Rows are per (face, layer) -- the
        # marking reaches every layer a change in `large` invalidates -- so count
        # faces, not rows.
        assert (
            db.run_query(
                "SELECT count(DISTINCT id) FROM map_bounds_topology.dirty_face"
            ).scalar()
            == 3
        )

        # Check that we have two maps in the map_area table
        assert n_map_areas(db) == 2

        # `large` and `medium` are unserved in the carto tree. Served here, so a
        # face below `carto-large` is credited to them, and the member faces
        # below have something to read.
        db.run_query(
            "UPDATE maps.sources SET is_served = true WHERE slug IN ('large', 'medium')"
        )
        db.session.commit()

        # Placement is authored. Nothing infers a layer from `scale` any more, so
        # a map that is never placed is ingested, assembled, and served nowhere --
        # which is why every test that adds a source also says where it goes.
        #
        # After bounds assembly, not before: a map reaches a layer only once it
        # has a boundary, and marking faces dirty in a layer the map cannot yet
        # hold territory in just makes work for the solver. This is the point in
        # the sequence the retired sweep wrote placements at, for the same reason.
        set_priority(db, "large", [(1001, 0), (1002, 0)])

    def test_dirty_faces(self, ctx):
        db = ctx.database

        with_topo = db.run_query(
            """
            SELECT a.source_id, s.slug, a.geometry_hash IS NOT NULL AS stamped,
                   (SELECT count(*) FROM map_bounds_topology.relation r
                     WHERE r.topogeo_id = (a.topo).id AND r.layer_id = (a.topo).layer_id) AS elements
            FROM map_bounds.map_area a JOIN maps.sources s USING (source_id)
            WHERE a.topo IS NOT NULL ORDER BY 1
            """
        ).all()
        assert len(with_topo) == 2, [tuple(r) for r in with_topo]

    def test_topology_is_valid(self, ctx):
        insp = TopologyInspector(ctx)
        assert insp.is_valid()

    def test_map_priority(self, ctx):
        db = ctx.database

        # Both maps are placed in the `large` compilation. A served layer is a
        # compilation like any other, so placement is an ordinary membership edge.
        assert (
            db.run_query(
                """
                SELECT count(*)
                FROM map_bounds.compilation_member cm
                JOIN maps.sources c ON c.source_id = cm.compilation_id
                WHERE c.slug = 'large'
                """
            ).scalar()
            == 2
        )

        # And they resolve in `large`, plus in `carto-large` by way of it -- rows
        # the flattening generates from `carto-large`'s membership. `carto`, the
        # multiscale compilation above, has no layer of its own.
        assert set(
            db.run_query(
                """
                SELECT DISTINCT s.slug
                FROM map_bounds.map_priority mp
                JOIN map_bounds.map_layer ml ON ml.id = mp.map_layer
                JOIN maps.sources s ON s.source_id = ml.source_id
                """
            ).scalars()
        ) == {"large", "carto-large"}

    def test_process_maps(self, ctx):
        # Check that we have the appropriate number of faces
        insp = TopologyInspector(ctx)
        assert insp.n_face_primitives() == 2

        # Update topology faces. The host pipeline, not the library's `update()`:
        # a face layer sync has just created is marked for the dissolve by
        # `mark-stale-identity`, which only the host runs.
        MacrostratTopologyManager(ctx).update_full()

        assert insp.n_faces(map_layer="Large") == 2

        # Sanity check that faces have been correctly identified
        args = (ctx.database, insp.map_layer_id("Large"))
        assert get_identity_for_area(*args, Point(0.5, 0.5)) == 1001
        assert get_identity_for_area(*args, Point(3.5, 0.5)) == 1002

    def test_add_overlapping_map(self, ctx):
        """Add a face that overlaps the other two"""
        db = ctx.database
        # This map overlaps the first two maps partially, creating three overlapping regions
        # with five total faces.
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES
                (1003, 'test_source_3', true, 'active', 'large')
            """
        )
        add_polygons(db, {1003: "ST_MakeEnvelope(1, 1, 4, 4, 4326)"})
        insp = TopologyInspector(ctx)
        mgr = TopologyManager(ctx)

        # Set the priority to this new map to 0, so it is prioritized under the others
        set_priority(db, "large", [(1003, 0)], default=1)

        update_maps(mgr, bulk=True)
        assert insp.n_face_primitives() == 5
        MacrostratTopologyManager(ctx).update_full()

        map_layer = insp.map_layer_id("Large")
        cases = [
            MapFaceTestCase(Point(0.5, 0.5), map_layer, 2),
            # The center face is at a lower priority than the other two,
            # so it only occupies the one face
            MapFaceTestCase(Point(2, 2), map_layer, 1),
            MapFaceTestCase(Point(4.5, 0.5), map_layer, 2),
            # Test face identity for shared areas
            MapFaceTestCase(Point(2.5, 1.5), map_layer, map_id=1003),
        ]

        for case in cases:
            # Get the face primitive in the center of the leftmost face
            case.validate(insp)

        # Check that there are three maps in the map_areas table
        assert n_map_areas(db) == 3
        # Number of overlapping primitives
        assert n_base_faces(db) == 3

    def test_map_reprioritization(self, ctx):
        """Check that the map faces are updated correctly when a map is reprioritized"""
        db = ctx.database
        mgr = TopologyManager(ctx)
        insp = TopologyInspector(ctx)

        # Set the priority of this new map to 10, so it is prioritized over the others
        set_priority(db, "large", [(1003, 10)], default=0)

        # We have to set the faces dirty
        _set_dirty(db, 1003)
        db.session.commit()

        # After reprioritization, the center face should be at priority 10, so it should occupy the two faces on either side of it
        # update_maps(mgr, bulk=True)
        assert insp.n_face_primitives() == 5
        MacrostratTopologyManager(ctx).update_full()

        # Check map identity for shared areas

        map_layer = insp.map_layer_id("Large")
        cases = [
            MapFaceTestCase(Point(0.5, 0.5), map_layer, 1, map_id=1001),
            # The center face is at a higher priority than the other two,
            # so it only occupies the one face
            MapFaceTestCase(Point(2.5, 2), map_layer, 2, map_id=1003),
            MapFaceTestCase(Point(4.5, 0.5), map_layer, 1, map_id=1002),
            MapFaceTestCase(Point(2.5, 1.5), map_layer, map_id=1003),
        ]

        for case in cases:
            # Get the face primitive in the center of the leftmost face
            case.validate(insp)

    def test_maps_are_separately_identified(self, ctx):
        """Check that the map faces have separate IDs"""
        db = ctx.database
        insp = TopologyInspector(ctx)
        id = insp.map_layer_id("Large")
        records = db.run_query(
            "SELECT * FROM map_bounds_topology.map_face WHERE map_layer = :map_layer",
            dict(map_layer=id),
        ).all()
        assert len(records) == 3
        assert len(set(record.map_id for record in records)) == 3

    def test_polygon_at_point_in_partly_covered_map(self, ctx):
        """A point resolves to the polygon under it, wherever that polygon's
        representative point falls.

        1003 now covers 1001's upper-right corner, so 1001's face is an L while
        its polygon is still the whole square, whose `ST_PointOnSurface` is the
        corner of the L. Testing faces against that point dropped 1001 at every
        point it still owns."""
        db = ctx.database

        for (x, y), map_id in [((0.5, 0.5), 1001), ((4.5, 0.5), 1002), ((2, 2), 1003)]:
            source_ids = db.run_query(
                """
                SELECT source_id FROM map_bounds.polygon_at(
                  'large', ST_SetSRID(ST_MakePoint(:x, :y), 4326), 10
                )
                """,
                dict(x=x, y=y),
            ).scalars()
            assert list(source_ids) == [map_id], (x, y)

        # The retired name answers the same, while API v2 still calls it.
        (alias,) = db.run_query(
            """
            SELECT source_id FROM map_bounds.units_at(
              'large', ST_SetSRID(ST_MakePoint(0.5, 0.5), 4326), 10
            )
            """
        ).one()
        assert alias == 1001

    def test_polygon_at_refuses_an_area(self, ctx):
        """An area is the legend's question."""
        db = ctx.database
        with raises(DBAPIError, match="takes a point"):
            db.run_query(
                """
                SELECT * FROM map_bounds.polygon_at(
                  'large', ST_MakeEnvelope(0, 0, 1, 1, 4326), 10
                )
                """
            ).all()
        db.session.rollback()

    ## TODO, we could add test isolation here with a template_database fixture...
    def test_add_another_layer_feature(self, ctx):
        """Add overlapping feature to the 'medium' layer to check that it is not merged into the 'large' layer.

        We use a large, circular feature to check whether we can also successfully work with maps that are subdivided
        on input.
        """
        db = ctx.database

        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES
                (1004, 'test_source_4', true, 'active', 'medium')
            """
        )
        add_polygons(
            db,
            {
                1004: "ST_SetSRID(ST_Buffer(ST_MakePoint(2, 2), 6, 'quad_segs=64'), 4326)"
            },
            scale="medium",
        )
        mgr = MacrostratTopologyManager(ctx)
        update_maps(mgr, subdivide_vertices=32)
        set_priority(db, "medium", [(1004, 0)])
        mgr.update_full()

        insp = TopologyInspector(ctx)
        assert n_base_faces(db) == 4
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Large") == 3

    def test_pieces_are_a_record_not_a_layer(self, ctx):
        """Pieces are cut, noded into the map's one topogeometry, and kept as a
        record; nothing about them is topological."""
        db = ctx.database
        pieces = db.run_query(
            """
            SELECT count(*) AS n, count(*) FILTER (WHERE noded) AS noded,
                   count(*) FILTER (WHERE topology_error IS NOT NULL) AS failed
            FROM map_bounds.map_topo WHERE source_id = 1004
            """
        ).one()
        assert pieces.n > 1
        assert pieces.noded == pieces.n
        assert pieces.failed == 0
        # One topogeometry per map, stamped complete.
        assert db.run_query(
            """
            SELECT topo IS NOT NULL AND geometry_hash = md5(ST_AsBinary(geometry))::uuid
            FROM map_bounds.map_area WHERE source_id = 1004
            """
        ).scalar()
        assert (
            db.run_query(
                """
                SELECT count(*) FROM topology.layer
                WHERE schema_name = 'map_bounds' AND table_name = 'map_topo'
                """
            ).scalar()
            == 0
        )

    def test_composite_layers(self, ctx):
        """A composite layer is solved like any other, not copied from its members.

        The flattened priority paths give it identity resolution, so the ordinary
        face pipeline dissolves it; nothing calls the painter's-algorithm overlay.
        Runs through `update_full`, the one command an operator uses, so the
        stale-identity marking and member-face sync run too.
        """
        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)
        mgr.update_full()
        insp = TopologyInspector(ctx)
        assert insp.n_faces(map_layer="Large") == 3
        assert insp.n_faces(map_layer="Medium") == 1
        # The carto tiers, each solved as a layer of its own. Beside the map
        # faces, a layer holds a member face for each served member it presents:
        # `large` and `medium`, served here (in the carto tree they are not, and
        # are skipped).
        assert n_faces(db, "carto-large") == (4, 2)
        assert n_faces(db, "carto-medium") == (1, 1)
        assert n_faces(db, "carto-small") == (0, 0)

        # Solved, not copied: an overlaid face carries a back-reference to the
        # member face it was cloned from.
        assert (
            db.run_query(
                """
                SELECT count(*) FROM map_bounds_topology.map_face mf
                WHERE map_bounds.is_composite_layer(mf.map_layer)
                  AND mf.source_id IS NOT NULL
                """
            ).scalar()
            == 0
        )

    def test_one_barrier_layer(self, ctx):
        """Every noded map records its boundary in the one barrier layer, which
        every solved layer composes -- so a map's bounds are a barrier in each
        layer that solves it, whatever its scale. The barrier layer is never
        solved, and neither a multiscale compilation nor one without members has
        a layer."""
        db = ctx.database
        barrier = db.run_query("SELECT map_bounds.barrier_layer()").scalar()
        assert barrier is not None

        misplaced = db.run_query(
            """
            SELECT count(*) FROM map_bounds.map_area
            WHERE topo IS NOT NULL
              AND map_layer IS DISTINCT FROM map_bounds.barrier_layer()
            """
        ).scalar()
        assert misplaced == 0

        solved = set(
            db.run_query(
                "SELECT DISTINCT map_layer FROM map_bounds.map_priority"
            ).scalars()
        )
        composing = set(
            db.run_query(
                """
                SELECT parent_id FROM map_bounds.map_layer_composition
                WHERE member_id = map_bounds.barrier_layer()
                """
            ).scalars()
        )
        assert solved and composing == solved
        assert barrier not in solved

        # `carto` draws its members' layers; `tiny` and `small` hold nothing here.
        assert (
            db.run_query(
                """
                SELECT count(*) FROM map_bounds.map_layer
                WHERE source_id IN (
                  map_bounds.source_id('carto'),
                  map_bounds.source_id('tiny'),
                  map_bounds.source_id('small')
                )
                """
            ).scalar()
            == 0
        )

    def test_world_opening(self, ctx):
        """`bounds open <map> world` then `bounds build` gives the map the whole
        world. The cache is filled on build, so the fold never seeds from NULL."""
        from macrostrat.map_topology.bounds import build as build_mod

        db = ctx.database
        build_mod.set_opening(db, 1001, "world")
        db.session.commit()

        dry = build_mod.build(db, 1001, dry_run=True)
        assert dry.error is None
        assert dry.area_km == approx(510_000_000, rel=0.01)

        res = build_mod.build(db, 1001)
        assert res.error is None
        assert res.written
        xmin, xmax = db.run_query(
            "SELECT ST_XMin(geometry), ST_XMax(geometry) FROM map_bounds.map_area WHERE source_id = 1001"
        ).first()
        assert (xmin, xmax) == (-180, 180)

    def test_build_skips_unchanged(self, ctx):
        """A rebuild writes only a boundary that moved beyond tolerance, and
        `needs_build` follows the operation list, not the geometry."""
        from macrostrat.map_topology.bounds import build as build_mod

        db = ctx.database
        assert 1001 not in build_mod.needs_build(db)

        res = build_mod.build(db, 1001)
        assert res.error is None
        assert res.unchanged and not res.written and res.diff_km == 0

        def punch(size):
            db.run_query(
                """
                UPDATE map_bounds.map_area
                SET geometry = ST_Multi(ST_Difference(
                  ST_MakeEnvelope(-180, -90, 180, 90, 4326),
                  ST_MakeEnvelope(0, 0, :size, :size, 4326)))
                WHERE source_id = 1001
                """,
                dict(size=size),
            )
            db.session.commit()

        # ~0.012 km²: drift on a world-sized boundary, not worth re-noding.
        punch(0.001)
        res = build_mod.build(db, 1001)
        assert res.unchanged and 0 < res.diff_km < build_mod.TOLERANCE_KM
        assert build_mod.build(db, 1001, strict=True).written

        # ~12,000 km² is over the absolute threshold, however small relatively.
        punch(1)
        res = build_mod.build(db, 1001)
        assert res.written and res.diff_km > build_mod.TOLERANCE_KM

        build_mod.set_opening(db, 1001, "world")
        db.session.commit()
        assert 1001 in build_mod.needs_build(db)
        assert build_mod.build(db, 1001).error is None

    def test_multiscale_carto(self, ctx):
        """`carto` is one multiscale compilation over the four served tiers, and
        a request at a zoom is answered by the member whose scale band contains
        it. The bands live in `scale_band` alone."""
        db = ctx.database

        mode, members = db.run_query(
            """
            SELECT c.assembly_mode,
              (SELECT array_agg(m.slug ORDER BY m.scale::maps.map_scale)
               FROM map_bounds.compilation_member cm
               JOIN maps.sources m ON m.source_id = cm.member_id
               WHERE cm.compilation_id = c.source_id)
            FROM map_bounds.compilation c
            JOIN maps.sources s ON s.source_id = c.source_id
            WHERE s.slug = 'carto'
            """
        ).first()
        assert mode == "multiscale"
        assert members == ["tiny", "carto-small", "carto-medium", "carto-large"]

        served = db.run_query(
            """
            SELECT z, s.slug
            FROM unnest(ARRAY[0, 2, 3, 5, 6, 8, 9, 18]) z
            JOIN maps.sources s
              ON s.source_id = map_bounds.serving_source(map_bounds.source_id('carto'), z)
            ORDER BY z
            """
        ).all()
        assert [slug for _, slug in served] == [
            "tiny",
            "tiny",
            "carto-small",
            "carto-small",
            "carto-medium",
            "carto-medium",
            "carto-large",
            "carto-large",
        ]

        # Anything that is not multiscale answers for itself at every zoom.
        (same,) = db.run_query(
            "SELECT map_bounds.serving_source(map_bounds.source_id('carto-large'), 0)"
        ).first()
        assert (
            same == db.run_query("SELECT map_bounds.source_id('carto-large')").scalar()
        )

        # `carto` has no faces of its own; its tiers do, served or not.
        carto_faces, served, tier_faces = db.run_query(
            """
            SELECT map_bounds.has_faces(map_bounds.source_id('carto')),
                   map_bounds.is_served(map_bounds.source_id('carto-large')),
                   map_bounds.has_faces(map_bounds.source_id('carto-large'))
            """
        ).first()
        assert (carto_faces, served, tier_faces) == (False, False, True)
        # The zoom picks the member, and its layer is what `carto` draws. Nothing
        # here is small-scale, so `carto-small`'s layer has no rankings and no
        # faces.
        for z, member, solved in [
            (5, "carto-small", False),
            (8, "carto-medium", True),
            (14, "carto-large", True),
        ]:
            layer, row = db.run_query(
                """
                SELECT map_bounds.face_layer_for(map_bounds.source_id('carto'), :z),
                  (SELECT id FROM map_bounds.map_layer
                   WHERE source_id = map_bounds.source_id(:member))
                """,
                dict(z=z, member=member),
            ).first()
            if solved:
                assert layer == row, z
            else:
                assert layer is None, z

        # Bounds: global by definition, seeded beside the layers'.
        opening, xmin, xmax = db.run_query(
            """
            SELECT o.operation, ST_XMin(a.geometry), ST_XMax(a.geometry)
            FROM map_bounds.boundary_op o
            JOIN map_bounds.map_area a ON a.source_id = o.source_id
            WHERE o.source_id = map_bounds.source_id('carto') AND o.position = 0
            """
        ).first()
        assert opening == "world"
        assert (xmin, xmax) == (-180, 180)

        # Idents: a slug, an id as text, or nothing.
        assert (
            db.run_query(
                "SELECT map_bounds.resolve_source(map_bounds.source_id('carto')::text)"
            ).scalar()
            == db.run_query("SELECT map_bounds.source_id('carto')").scalar()
        )
        assert (
            db.run_query("SELECT map_bounds.resolve_source('no-such')").scalar() is None
        )

        # The legacy alias reads `carto.polygons`, empty here, and an unknown name
        # is nothing rather than an error. Asked away from the test maps, which
        # `carto` would otherwise answer with.
        point = "ST_SetSRID(ST_MakePoint(100, 50), 4326)"
        for ident in ("sys:carto-legacy", "no-such", "carto"):
            n = db.run_query(
                f"SELECT count(*) FROM map_bounds.polygon_at(:ident, {point}, 10)",
                dict(ident=ident),
            ).scalar()
            assert n == 0, ident

    def test_virtual_compilation(self, ctx):
        """A compilation with no polygons of its own is descended through.

        Identity resolves to whichever member actually holds the geometry, so a
        compilation can be named and referred to without being materialized.
        """
        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)
        insp = TopologyInspector(ctx)

        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES (1005, 'test_source_5', false, 'active', 'large')
            """
        )
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
            VALUES (1005, 1001, 1), (1005, 1002, 2)
            """
        )
        # Sources 1 and 2 are now placed *through* the compilation, not beside
        # it, so their own edges in `large` come out. The sweep used to do this
        # on the next sync; it is an authored act now, and this is the same pair
        # of writes `compilations add --reparent` makes.
        set_priority(db, "large", [(1005, 0)])
        db.run_query(
            """
            DELETE FROM map_bounds.compilation_member cm
            USING maps.sources c
            WHERE c.slug = 'large'
              AND cm.compilation_id = c.source_id
              AND cm.member_id IN (1001, 1002)
            """
        )
        db.session.commit()

        update_maps(mgr, bulk=True)

        # A compilation's bounds come from the `compile` opening operation: the
        # union of the noded sources below it, composed like any map's bounds.
        stored, members, area_km, opening = db.run_query(
            """
            SELECT
              ST_Area(a.geometry),
              (SELECT ST_Area(ST_Union(geometry)) FROM map_bounds.map_area
               WHERE source_id IN (1001, 1002)),
              a.area_km,
              (SELECT operation FROM map_bounds.boundary_op
               WHERE source_id = 1005 AND position = 0)
            FROM map_bounds.map_area a WHERE a.source_id = 1005
            """
        ).first()
        assert opening == "compile"
        assert stored == approx(members, rel=1e-9)
        assert area_km is not None and area_km > 0
        # A compilation has no topogeometry: it is never parted out, and identity
        # resolves a materialized one through its members.
        assert db.run_query(
            "SELECT topo IS NULL FROM map_bounds.map_area WHERE source_id = 1005"
        ).scalar()
        # Its bounds are stamped complete, so it never reads as needing noding.
        assert db.run_query(
            "SELECT is_current FROM map_bounds.map_area_sync WHERE source_id = 1005"
        ).scalar()

        layer = insp.map_layer_id("Large")
        rows = dict(
            db.run_query(
                """
                SELECT map_id, priority_path
                FROM map_bounds.map_priority
                WHERE map_layer = :layer
                """,
                dict(layer=layer),
            ).all()
        )
        # The members carry the compilation's standing plus their own, and the
        # compilation itself is not a resolution target -- it holds no polygons.
        assert 1005 not in rows
        assert {1001, 1002} <= set(rows)
        assert rows[1001][-1] == 1 and rows[1002][-1] == 2
        assert rows[1001][:-1] == rows[1002][:-1]
        # One hop deeper than a map placed directly in the layer.
        assert len(rows[1001]) == len(rows[1003]) + 1

        # Identity lands on a member, never on the virtual compilation.
        assert get_identity_for_area(db, layer, Point(0.5, 0.5)) == 1001
        assert get_identity_for_area(db, layer, Point(3.5, 0.5)) == 1002

    def test_retired_mosaic_member(self, ctx):
        """A noded map that becomes a mosaic-only member is released by update.

        Its extent is its bounds from then on, so its topogeometry is dead weight
        -- SGMC's members were noded before mosaics existed and kept theirs.
        """
        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)

        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES (1007, 'test_source_7', true, 'active', 'large')
            """
        )
        add_polygons(db, {1007: "ST_MakeEnvelope(10, 10, 11, 11, 4326)"})
        update_maps(mgr)

        def held():
            return db.run_query(
                """
                SELECT topo IS NOT NULL OR EXISTS (
                  SELECT 1 FROM map_bounds.map_topo t WHERE t.source_id = 1007
                ) FROM map_bounds.map_area WHERE source_id = 1007
                """
            ).scalar()

        assert held()
        assert 1007 in {m.map_id for m in get_map_list(db)}

        for statement in (
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES (1008, 'test_source_8', false, 'active', 'large')
            """,
            """
            INSERT INTO map_bounds.compilation (source_id, assembly_mode)
            VALUES (1008, 'mosaic')
            """,
            """
            INSERT INTO map_bounds.compilation_member (compilation_id, member_id, priority)
            VALUES (1008, 1007, 0)
            """,
        ):
            db.run_query(statement)
        db.session.commit()

        assert 1007 not in {m.map_id for m in get_map_list(db)}
        assert 1007 in {m.map_id for m in get_retired_maps(db)}
        # `topo remove` can still reach it.
        assert 1007 in {m.map_id for m in get_held_maps(db)}

        summary = update_maps(mgr)
        assert summary.maps_released == 1
        assert not held()
        assert get_retired_maps(db) == []

    def test_one_piece_at_a_time(self, ctx):
        """Pieces noded singly give the same result, and a piece that runs past
        `piece_timeout` is recorded as failed rather than stalling the run."""
        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)

        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES (1011, 'test_source_11', true, 'active', 'large'),
                   (1012, 'test_source_12', true, 'active', 'large')
            """
        )
        # Thousands of vertices, so each is cut into several pieces.
        add_polygons(
            db,
            {
                1011: "ST_Buffer(ST_MakePoint(20, 20)::geography, 50000, 1000)::geometry",
                1012: "ST_Buffer(ST_MakePoint(30, 20)::geography, 50000, 1000)::geometry",
            },
        )

        def pieces(map_id):
            return db.run_query(
                """
                SELECT count(*) AS n, count(*) FILTER (WHERE noded) AS noded,
                  count(*) FILTER (WHERE topology_error LIKE 'timed out%') AS timed_out
                FROM map_bounds.map_topo WHERE source_id = :map_id
                """,
                dict(map_id=map_id),
            ).one()

        update_maps(mgr, ["test_source_11"], one_at_a_time=True)
        p = pieces(1011)
        assert p.n > 1 and p.noded == p.n

        update_maps(mgr, ["test_source_12"], piece_timeout=0.001)
        p = pieces(1012)
        assert p.n > 1 and p.timed_out > 0 and p.noded + p.timed_out == p.n

        release_map(db, 1012)
        db.session.commit()

    def test_vacuum_topology(self, ctx):
        """Compaction runs outside a transaction and leaves the primitives intact."""
        db = ctx.database
        count = "SELECT count(*) FROM map_bounds_topology.edge_data"
        edges = db.run_query(count).scalar()
        vacuum_topology(db)
        assert db.run_query(count).scalar() == edges

    def test_grid(self, ctx):
        """Grid lines split faces without changing what any map owns: their edges
        survive cleaning, every map's barrier rows stay complete, no solved layer
        is marked, and identity resolves as before.

        Two maps of its own, away from the rest of the suite's. The late tests
        leave the shared layers in a state where the solve builds no faces for a
        new map (one world-sized map, mosaics), so what the solve produces is not
        compared here; the barrier and attribution checks are what the grid can
        break, and they are checked directly."""
        from mapboard.topology_manager.commands.edge_relations import (
            validate_edge_relations,
        )

        from macrostrat.map_topology.grid import node_grid, seed_grid

        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)
        insp = TopologyInspector(ctx)
        layer = insp.map_layer_id("Large")
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, is_finalized, status_code, scale)
            VALUES
                (1021, 'test_source_21', true, 'active', 'large'),
                (1022, 'test_source_22', true, 'active', 'large')
            """
        )
        add_polygons(
            db,
            {
                1021: "ST_MakeEnvelope(20, 0, 24, 4, 4326)",
                1022: "ST_MakeEnvelope(22, 2, 26, 6, 4326)",
            },
        )
        set_priority(db, "large", [(1021, 5), (1022, 6)])
        points = [Point(21, 1), Point(23, 3), Point(25, 5)]

        mgr.update_full()
        ids_before = [get_identity_for_area(db, layer, p) for p in points]
        assert ids_before == [1021, 1022, 1022]
        primitives_before = insp.n_face_primitives()
        assert validate_edge_relations(ctx).in_sync

        # 2° lines over the two maps: they cross both maps' interiors and split
        # their edges (x = 22, 24; y = 2, 4).
        assert seed_grid(db, levels=(2,), extent=(18, -2, 28, 8)) > 0
        noded, failed = node_grid(db, levels=(2,))
        assert noded > 0 and failed == 0
        assert insp.n_face_primitives() > primitives_before

        # The segments' marks are gone and nothing fanned out to a solved layer.
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 0
        )
        # A segment splits a map's edge without splitting a face; the new half
        # must still carry its owner's barrier row.
        report = validate_edge_relations(ctx)
        assert report.missing == 0 and report.extra == 0

        mgr.clean_topology()
        orphaned = db.run_query(
            """
            SELECT count(*) FROM map_bounds.grid_line g
            WHERE NOT EXISTS (
              SELECT 1 FROM map_bounds_topology.relation r
              WHERE r.topogeo_id = (g.topo).id AND r.layer_id = (g.topo).layer_id
            )
            """
        ).scalar()
        assert orphaned == 0
        assert validate_edge_relations(ctx).in_sync

        mgr.update_full()
        assert [get_identity_for_area(db, layer, p) for p in points] == ids_before


@dataclass
class MapFaceTestCase:
    location: Point
    map_layer: str
    # Number of adjacent faces expected to be dissolved into this map_face
    n_face_primitives: int = None
    # Expected map_id for the face
    map_id: int = None

    def validate(self, insp):
        center = geom(self.location)
        face_id = insp.get_face_id(center)
        face_list = insp.get_adjacent_faces(face_id, self.map_layer)
        if self.n_face_primitives is None:
            self.n_face_primitives = len(face_list)
            assert len(face_list) == self.n_face_primitives
        if self.map_id is not None:
            assert self.map_id == get_identity_for_area(
                insp.db, self.map_layer, self.location
            )


def n_map_areas(db):
    """Count maps, not compilations -- every compilation has a `map_area` row too,
    composed from its members' bounds, and the scale compilations have one before
    they have members."""
    return db.run_query(
        """
        SELECT count(*) FROM map_bounds.map_area a
        WHERE map_bounds.has_content(a.source_id)
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.compilation_member cm
            WHERE cm.compilation_id = a.source_id
          )
        """
    ).scalar()


@dataclass
class MapPriority:
    map_id: int
    priority: int


type MapID = int
type MapPriority = tuple[MapID, int]

from typing import Iterable


def set_priority(
    db,
    map_layer: str,
    priority: Iterable[MapPriority],
    *,
    default: int = None,
):
    """
    Set priority for maps within a layer's compilation.
    """
    if default is not None:
        db.run_query(
            """
            UPDATE map_bounds.compilation_member cm
            SET priority = :default_priority
            FROM maps.sources c
            WHERE c.slug = :layer
              AND cm.compilation_id = c.source_id
            """,
            dict(default_priority=default, layer=map_layer),
        )
    db.run_query(
        """
        INSERT INTO map_bounds.compilation_member
            (compilation_id, member_id, priority)
        SELECT c.source_id, :map_id, :priority
        FROM maps.sources c
        WHERE c.slug = :layer
        ON CONFLICT (compilation_id, member_id)
        DO UPDATE SET priority = EXCLUDED.priority
        """,
        params=[dict(map_id=p[0], priority=p[1], layer=map_layer) for p in priority],
    )
    # Paths are derived from the edges, so an edit only takes effect once they
    # are rebuilt.
    db.run_sql(proc("sync-priority-paths"))
    db.session.commit()


def n_base_faces(db):
    """Faces in the scale compilations' layers (`large`, `medium`), not the carto
    tiers'. `TopologyInspector.n_faces()` counts every layer."""
    return db.run_query(
        """
        SELECT count(*) FROM map_bounds_topology.map_face mf
        JOIN map_bounds.map_layer ml ON ml.id = mf.map_layer
        WHERE ml.source_id IN (
          map_bounds.source_id('large'), map_bounds.source_id('medium')
        )
        """
    ).scalar()


def add_polygons(db, geometries: dict[int, str], *, scale: str = "large"):
    """Give each source a polygon, so a boundary can be unioned from it."""
    for source_id, geometry in geometries.items():
        db.run_query(
            """
            INSERT INTO maps.polygons (source_id, scale, geom)
            VALUES (:source_id, :scale, ST_Multi({geometry}))
            """.replace("{geometry}", geometry),
            dict(source_id=source_id, scale=scale),
        )
    db.session.commit()


def n_faces(db, compilation: str) -> tuple[int, int]:
    """A layer's map faces and member faces, apart. A member face belongs to a
    compilation (`sync-unit-faces`), which has no content of its own."""
    row = db.run_query(
        """
        SELECT
          count(*) FILTER (WHERE map_bounds.has_content(mf.map_id)),
          count(*) FILTER (WHERE NOT map_bounds.has_content(mf.map_id))
        FROM map_bounds_topology.map_face mf
        JOIN map_bounds.map_layer ml ON ml.id = mf.map_layer
        WHERE ml.source_id = map_bounds.source_id(:compilation)
        """,
        dict(compilation=compilation),
    ).one()
    return tuple(row)


def get_identity_for_area(db, map_layer: int, geometry):
    return db.run_query(
        "SELECT map_bounds_topology.identity_for_area(:geometry, :map_layer)",
        dict(map_layer=map_layer, geometry=geom(geometry)),
    ).scalar()
