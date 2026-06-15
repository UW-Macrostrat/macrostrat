from macrostrat.map_topology import create_fixtures, update_maps, create_topo_context
from mapboard.topology_manager.tests.helpers import TopologyInspector
from mapboard.topology_manager.commands.update import _update


class TestMapTopology:
    def test_map_topology(self, test_db_base):
        # Need to work on test isolation here...
        create_fixtures(test_db_base)

    def test_create_map_bounds(self, test_db_base):
        """Insert a few test maps into the database

        They have overlapping bounds so we can test the logic for merging them into
        a composite layer.
        """
        db = test_db_base

        # Insert some test map sources
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code, scale)
            VALUES
                (1, 'test_source', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active', 'large'),
                (2, 'test_source_2', ST_MakeEnvelope(1, 1, 3, 3, 4326), true, 'active', 'large');
            """
        )

        update_maps(db, clean=False)

        # Check that we have two maps in the map_area table
        assert db.run_query("SELECT count(*) FROM map_bounds.map_area").scalar() == 2

    def test_dirty_faces(self, test_db_base):
        db = test_db_base

        assert (
            db.run_query(
                "SELECT count(topo) FROM map_bounds.map_area WHERE topo IS NOT NULL"
            ).scalar()
            == 2
        )
        # Check that we have three dirty faces in the dirty_face table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds_topology.dirty_face").scalar()
            == 2
        )

    def test_map_compilations(self, test_db_base):
        db = test_db_base

        # Check that we have two map compilations in the map_compilation table
        assert (
            db.run_query("SELECT count(*) FROM map_bounds.map_compilation").scalar()
            == 2
        )

    def test_process_maps(self, test_db_base):
        # Check that we have the appropriate number of faces
        db = test_db_base
        ctx = create_topo_context(db)
        insp = TopologyInspector(ctx)
        assert insp.n_face_primitives() == 3

        # Force faces to dirty
        db.run_sql(
            """INSERT INTO map_bounds_topology.dirty_face (map_layer, id)
            SELECT ml.id, face_id FROM map_bounds_topology.face
            CROSS JOIN map_bounds.map_layer ml;
            """
        )
        db.session.commit()

        # Update topology faces
        _update(ctx)

        assert insp.n_faces() == 2
