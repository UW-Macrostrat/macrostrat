from macrostrat.map_topology import create_fixtures, update_maps, create_topo_context
from mapboard.topology_manager.tests.helpers import TopologyInspector
from mapboard.topology_manager.commands.update import _update
from pytest import fixture


@fixture
def ctx(test_db_base):
    return create_topo_context(test_db_base)


class TestMapTopology:
    def test_map_topology(self, ctx):
        # TODO: Need to work on test isolation here...
        create_fixtures(ctx)

    def test_create_map_bounds(self, test_db_base):
        """Insert a few test maps into the database

        They have overlapping bounds so we can test the logic for merging them into
        a composite layer.
        """
        ctx = create_topo_context(test_db_base)
        db = ctx.database

        # Insert some test map sources
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1, 'test_source', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active', 'large'),
                (2, 'test_source_2', ST_MakeEnvelope(1, 1, 3, 3, 4326), true, 'active', 'large');
            """
        )

        update_maps(ctx)

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
        # Check that we have three dirty faces in the dirty_face table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 3
        )

    def test_map_compilations(self, ctx):
        db = ctx.database

        # Check that we have two map compilations in the map_compilation table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds.map_compilation").scalar()
            == 2
        )

    def test_process_maps(self, ctx):
        # Check that we have the appropriate number of faces
        insp = TopologyInspector(ctx)
        assert insp.n_face_primitives() == 3

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
