from macrostrat.map_topology import create_fixtures, update_maps


class TestMapTopology:
    def test_map_topology(self, test_db_base):
        create_fixtures(test_db_base)

    def test_create_map_bounds(self, test_db):
        """Insert a few test maps into the database

        They have overlapping bounds so we can test the logic for merging them into
        a composite layer.
        """
        db = test_db

        # Insert some test map sources
        db.run_query(
            """
            INSERT INTO maps.sources (source_id, slug, rgeom, is_finalized, status_code)
            VALUES
                (1, 'test_source', ST_MakeEnvelope(0, 0, 2, 2, 4326), true, 'active'),
                (2, 'test_source_2', ST_MakeEnvelope(1, 1, 3, 3, 4326), true, 'active');
            """
        )

        update_maps(db)

        # Check that we have two maps in the map_area table
        assert db.run_query("SELECT count(*) FROM map_bounds.map_area").scalar() == 2
