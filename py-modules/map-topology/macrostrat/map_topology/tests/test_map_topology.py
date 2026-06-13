from macrostrat.map_topology import create_fixtures


def test_map_topology(test_db_base):
    create_fixtures(test_db_base)
