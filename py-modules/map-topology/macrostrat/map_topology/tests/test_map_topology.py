from pytest import mark
from geoalchemy2.shape import from_shape
from prompt_toolkit.styles.style import default_priority

from mapboard.topology_manager import TopologyInspector, TopologyManager
from pytest import fixture
from shapely.geometry import Point
from dataclasses import dataclass

from macrostrat.map_topology import create_topo_context, _set_dirty, _update_identity
from macrostrat.map_topology.manager import MacrostratTopologyManager, update_maps


def geom(_shape, srid=4326):
    return str(from_shape(_shape, srid, extended=True))


@fixture(scope="class")
def ctx(test_db_base):
    yield create_topo_context(test_db_base)


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
                (1, 'test_source_1', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active', 'large'),
                (2, 'test_source_2', ST_MakeEnvelope(3, 0, 5, 2, 4326), true, 'active', 'large');
            """
        )

        update_maps(mgr, bulk=True)

        # Check that we have three dirty faces in the dirty_face table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 3
        )

        # Check that we have two maps in the map_area table
        assert n_map_areas(db) == 2

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

        # Check that we have two maps in the priority table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds.map_priority").scalar() == 2
        )

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
        assert get_identity_for_area(*args, Point(0.5, 0.5)) == 1
        assert get_identity_for_area(*args, Point(3.5, 0.5)) == 2

    def test_add_overlapping_map(self, ctx):
        """Add a face that overlaps the other two"""
        db = ctx.database
        # This map overlaps the first two maps partially, creating three overlapping regions
        # with five total faces.
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (3, 'test_source_3', ST_MakeEnvelope(1, 1, 4, 4, 4326), true, 'active', 'large')
            """
        )
        insp = TopologyInspector(ctx)
        mgr = TopologyManager(ctx)

        # Set the priority to this new map to 0, so it is prioritized under the others
        set_priority(db, "large", [(3, 0)], default=1)

        update_maps(mgr, bulk=True)
        assert insp.n_face_primitives() == 5
        mgr.update(composite_layers=False)

        map_layer = insp.map_layer_id("Large")
        cases = [
            MapFaceTestCase(Point(0.5, 0.5), map_layer, 2),
            # The center face is at a lower priority than the other two,
            # so it only occupies the one face
            MapFaceTestCase(Point(2, 2), map_layer, 1),
            MapFaceTestCase(Point(4.5, 0.5), map_layer, 2),
            # Test face identity for shared areas
            MapFaceTestCase(Point(2.5, 1.5), map_layer, map_id=3),
        ]

        for case in cases:
            # Get the face primitive in the center of the leftmost face
            case.validate(insp)

        # Check that there are three maps in the map_areas table
        assert n_map_areas(db) == 3
        # Number of overlapping primitives
        assert insp.n_faces() == 3

    def test_map_reprioritization(self, ctx):
        """Check that the map faces are updated correctly when a map is reprioritized"""
        db = ctx.database
        mgr = TopologyManager(ctx)
        insp = TopologyInspector(ctx)

        # Set the priority of this new map to 10, so it is prioritized over the others
        set_priority(db, "large", [(3, 10)], default=0)

        # We have to set the faces dirty
        _set_dirty(db, 3)
        db.session.commit()

        # After reprioritization, the center face should be at priority 10, so it should occupy the two faces on either side of it
        # update_maps(mgr, bulk=True)
        assert insp.n_face_primitives() == 5
        mgr.update(composite_layers=False)

        # Check map identity for shared areas

        map_layer = insp.map_layer_id("Large")
        cases = [
            MapFaceTestCase(Point(0.5, 0.5), map_layer, 1, map_id=1),
            # The center face is at a higher priority than the other two,
            # so it only occupies the one face
            MapFaceTestCase(Point(2.5, 2), map_layer, 2, map_id=3),
            MapFaceTestCase(Point(4.5, 0.5), map_layer, 1, map_id=2),
            MapFaceTestCase(Point(2.5, 1.5), map_layer, map_id=3),
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
                (4, 'test_source_4', ST_SetSRID(ST_Buffer(ST_MakePoint(2, 2), 6, 'quad_segs=64'), 4326), true, 'active', 'medium')
            """
        )

        mgr = MacrostratTopologyManager(ctx)
        update_maps(mgr, subdivide_vertices=32)
        mgr.update(composite_layers=False)

        insp = TopologyInspector(ctx)
        assert insp.n_faces() == 4
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Large") == 3

    def test_composite_layers(self, ctx):

        mgr = MacrostratTopologyManager(ctx)
        mgr.update(composite_layers=True)
        insp = TopologyInspector(ctx)
        assert insp.n_faces(map_layer="Large") == 3
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Carto large") == 4
        assert insp.n_faces(map_layer="Carto medium") == 1
        assert insp.n_faces(map_layer="Carto small") == 0
        assert insp.n_faces() == 4 + 4 + 1


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
    return db.run_query("SELECT count(*) FROM map_bounds.map_area").scalar()


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
    Set priority for maps in a layer
    """
    tbl = db.get_table("map_bounds.map_priority")
    if default is None:
        db.run_query(
            "UPDATE map_bounds.map_priority SET priority = :default_priority",
            dict(default_priority=default),
        )
    db.run_query(
        """
        INSERT INTO map_bounds.map_priority
            (map_id, priority, map_layer)
        VALUES
            (:map_id, :priority, map_bounds.layer_id(:layer_id))
        ON CONFLICT (map_id, map_layer) DO UPDATE SET priority = EXCLUDED.priority
        """,
        params=[dict(map_id=p[0], priority=p[1], layer_id=map_layer) for p in priority],
    )
    db.session.commit()


def get_identity_for_area(db, map_layer: int, geometry):
    return db.run_query(
        "SELECT map_bounds_topology.identity_for_area(:geometry, :map_layer)",
        dict(map_layer=map_layer, geometry=geom(geometry)),
    ).scalar()
