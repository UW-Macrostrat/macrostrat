from dataclasses import dataclass

from geoalchemy2.shape import from_shape
from mapboard.topology_manager import TopologyInspector, TopologyManager
from prompt_toolkit.styles.style import default_priority
from pytest import approx, fixture, mark
from shapely.geometry import Point

from macrostrat.map_topology import _set_dirty, _update_identity
from macrostrat.map_topology.config import create_topo_context
from macrostrat.map_topology.manager import (
    MacrostratTopologyManager,
    proc,
    update_maps,
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
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1001, 'test_source_1', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active', 'large'),
                (1002, 'test_source_2', ST_MakeEnvelope(3, 0, 5, 2, 4326), true, 'active', 'large');
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

        # Check that we have three dirty faces in the dirty_face table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 3
        )

        # Check that we have two maps in the map_area table
        assert n_map_areas(db) == 2

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

        assert (
            db.run_query(
                "SELECT count(topo) FROM map_bounds.map_area WHERE topo IS NOT NULL"
            ).scalar()
            == 2
        )

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
                JOIN map_bounds.map_layer ml ON ml.source_id = cm.compilation_id
                WHERE ml.slug = 'large'
                """
            ).scalar()
            == 2
        )

        # And they resolve in `large`, plus in `carto-large` by way of it --
        # rows the flattening generates, which is what lets a composite layer be
        # solved rather than copied.
        assert set(
            db.run_query(
                """
                SELECT DISTINCT ml.slug
                FROM map_bounds.map_priority mp
                JOIN map_bounds.map_layer ml ON ml.id = mp.map_layer
                """
            ).scalars()
        ) == {"large", "carto-large"}

    def test_process_maps(self, ctx):
        # Check that we have the appropriate number of faces
        insp = TopologyInspector(ctx)
        assert insp.n_face_primitives() == 2
        mgr = TopologyManager(ctx)

        # Update topology faces
        mgr.update()

        assert insp.n_faces() == 2

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
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1003, 'test_source_3', ST_MakeEnvelope(1, 1, 4, 4, 4326), true, 'active', 'large')
            """
        )
        add_polygons(db, {1003: "ST_MakeEnvelope(1, 1, 4, 4, 4326)"})
        insp = TopologyInspector(ctx)
        mgr = TopologyManager(ctx)

        # Set the priority to this new map to 0, so it is prioritized under the others
        set_priority(db, "large", [(1003, 0)], default=1)

        update_maps(mgr, bulk=True)
        assert insp.n_face_primitives() == 5
        mgr.update()

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
        mgr.update()

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

    ## TODO, we could add test isolation here with a template_database fixture...
    def test_add_another_layer_feature(self, ctx):
        """Add overlapping feature to the 'medium' layer to check that it is not merged into the 'large' layer.

        We use a large, circular feature to check whether we can also successfully work with maps that are subdivided
        on input.
        """
        db = ctx.database

        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1004, 'test_source_4', ST_SetSRID(ST_Buffer(ST_MakePoint(2, 2), 6, 'quad_segs=64'), 4326), true, 'active', 'medium')
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
        mgr.update()

        insp = TopologyInspector(ctx)
        assert n_base_faces(db) == 4
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Large") == 3

    def test_composite_layers(self, ctx):
        """A composite layer is solved like any other, not copied from its members.

        The flattened priority paths give it identity resolution, so the ordinary
        face pipeline dissolves it; nothing calls the painter's-algorithm overlay.
        """
        db = ctx.database
        mgr = MacrostratTopologyManager(ctx)
        mgr.update()
        insp = TopologyInspector(ctx)
        assert insp.n_faces(map_layer="Large") == 3
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Carto large") == 4
        assert insp.n_faces(map_layer="Carto medium") == 1
        assert insp.n_faces(map_layer="Carto small") == 0

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
            USING map_bounds.map_layer ml
            WHERE ml.slug = 'large'
              AND cm.compilation_id = ml.source_id
              AND cm.member_id IN (1001, 1002)
            """
        )
        db.session.commit()

        update_maps(mgr, bulk=True)

        # The stored geometry is only an envelope -- cheap, and enough to say
        # roughly where the compilation is. The exact footprint stays in
        # `composite_topo`, resolved on demand.
        stored, exact, members, area_km = db.run_query(
            """
            SELECT
              ST_Area(a.geometry),
              ST_Area(a.composite_topo::geometry),
              (SELECT ST_Area(ST_Union(geometry)) FROM map_bounds.map_area
               WHERE source_id IN (1001, 1002)),
              a.area_km
            FROM map_bounds.map_area a WHERE a.source_id = 1005
            """
        ).first()
        # A region-scale compilation stores its real boundary, not an envelope.
        assert stored == approx(exact, rel=1e-9)
        assert exact == approx(members, rel=1e-9)
        assert area_km is not None and area_km > 0

        # It references its members' topogeometries rather than re-listing every
        # face they cover -- one element per member, at any nesting depth.
        assert set(
            db.run_query(
                """
                SELECT a2.source_id
                FROM map_bounds.map_area a
                JOIN map_bounds_topology.relation r
                  ON r.layer_id = (a.composite_topo).layer_id
                 AND r.topogeo_id = (a.composite_topo).id
                JOIN map_bounds.map_area a2
                  ON (a2.topo).id = r.element_id
                 AND (a2.topo).layer_id = r.element_type
                WHERE a.source_id = 1005
                """
            ).scalars()
        ) == {1001, 1002}

        # A compilation lives in the composite layer, not the primitive one.
        assert db.run_query(
            "SELECT topo IS NULL AND composite_topo IS NOT NULL"
            " FROM map_bounds.map_area WHERE source_id = 1005"
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
    assembled from its members' faces."""
    return db.run_query(
        """
        SELECT count(*) FROM map_bounds.map_area a
        WHERE NOT map_bounds.has_faces(a.source_id)
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
            FROM map_bounds.map_layer ml
            WHERE ml.slug = :layer
              AND cm.compilation_id = ml.source_id
            """,
            dict(default_priority=default, layer=map_layer),
        )
    db.run_query(
        """
        INSERT INTO map_bounds.compilation_member
            (compilation_id, member_id, priority)
        SELECT ml.source_id, :map_id, :priority
        FROM map_bounds.map_layer ml
        WHERE ml.slug = :layer
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
    """Faces in ordinary layers. `TopologyInspector.n_faces()` counts every layer,
    and composite layers are solved now, so a bare total no longer isolates the
    base ones."""
    return db.run_query(
        """
        SELECT count(*) FROM map_bounds_topology.map_face mf
        WHERE NOT map_bounds.is_composite_layer(mf.map_layer)
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


def get_identity_for_area(db, map_layer: int, geometry):
    return db.run_query(
        "SELECT map_bounds_topology.identity_for_area(:geometry, :map_layer)",
        dict(map_layer=map_layer, geometry=geom(geometry)),
    ).scalar()
