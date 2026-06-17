from sqlalchemy.dialects.postgresql import insert

from macrostrat.map_topology import create_fixtures, update_maps, create_topo_context
from mapboard.topology_manager.tests.helpers import TopologyInspector
from mapboard.topology_manager.commands.update import _update
from mapboard.topology_manager.commands.update_faces.helpers import get_adjacent_faces
from pytest import fixture
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from macrostrat.database.utils import template_database
from macrostrat.database import Database


def geom(_shape, srid=4326):
    return str(from_shape(_shape, srid, extended=True))


@fixture(scope="class")
def ctx(test_db_base):
    with template_database(test_db_base.engine) as engine:
        db = Database(engine)
        yield create_topo_context(db)


class TestMapTopology:
    def test_map_topology(self, ctx):
        # TODO: Need to work on test isolation here...
        create_fixtures(ctx)

    def test_create_map_bounds(self, ctx):
        """Insert a few test maps into the database

        They have overlapping bounds so we can test the logic for merging them into
        a composite layer.
        """
        db = ctx.database

        # Insert two non-overlapping test sources
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1, 'test_source_1', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active', 'large'),
                (2, 'test_source_2', ST_MakeEnvelope(3, 0, 5, 2, 4326), true, 'active', 'large');
            """
        )

        update_maps(ctx)

        # Check that we have three dirty faces in the dirty_face table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 3
        )

        # Check that we have two maps in the map_area table
        assert db.run_query("SELECT count(*) FROM map_bounds.map_area").scalar() == 2

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

        # Force faces to dirty
        # db.run_sql(
        #     """INSERT INTO map_bounds_topology.dirty_face (map_layer, id)
        #     SELECT ml.id, face_id FROM map_bounds_topology.face
        #     CROSS JOIN map_bounds.map_layer ml;
        #     """
        # )
        # db.session.commit()

        # Update topology faces
        _update(ctx)

        assert insp.n_faces() == 2

    def test_add_overlapping_map(self, ctx):
        """Add a face that overlaps the other two"""
        db = ctx.database
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (3, 'test_source_3', ST_MakeEnvelope(1, 1, 4, 4, 4326), true, 'active', 'large')
            """
        )
        insp = TopologyInspector(ctx)

        update_maps(ctx)

        assert insp.n_face_primitives() == 5

        _update(ctx, composite_layers=False)

        # Get the face primitive in the center of the new face
        center = geom(Point(2.5, 2.5))
        face_id = insp.get_face_id(center)
        map_layer = insp.map_layer_id("Large")
        face_list = get_adjacent_faces(db, face_id, map_layer)

        assert len(face_list) == 3

        assert insp.n_faces() == 3

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

        update_maps(ctx, subdivide_vertices=32)
        _update(ctx, composite_layers=False)

        insp = TopologyInspector(ctx)
        assert insp.n_faces() == 4
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Large") == 3

    def test_composite_layers(self, ctx):

        _update(ctx, composite_layers=True)
        insp = TopologyInspector(ctx)
        assert insp.n_faces(map_layer="Large") == 3
        assert insp.n_faces(map_layer="Medium") == 1
        assert insp.n_faces(map_layer="Carto large") == 4
        assert insp.n_faces(map_layer="Carto medium") == 1
        assert insp.n_faces(map_layer="Carto small") == 0
        assert insp.n_faces() == 4 + 4 + 1
