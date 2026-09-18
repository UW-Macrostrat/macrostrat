"""The compilation graph routes.

Written against whatever compilations the test database happens to hold, since
the membership table is seeded by `compilations sync` rather than by a fixture:
the invariants below hold for any member set, including an empty one.
"""

from fastapi.testclient import TestClient

from .test_database import TEST_SOURCE_TABLE, api_client


class TestCompilations:
    def test_list(self, api_client: TestClient):
        response = api_client.get("/compilations")
        assert response.status_code == 200

        for node in response.json():
            # The node set *is* the set of maps with members, so this is the one
            # thing the index cannot return.
            assert node["is_compilation"]
            assert node["n_members"] > 0
            # A compilation resolves to at least as many maps as it directly
            # contains -- descending a member compilation can only add.
            assert node["n_sources"] >= node["n_members"]
            # Materialization is a compilation that holds its own polygons.
            assert node["is_materialized"] == node["holds_polygons"]

    def test_detail_of_each_compilation(self, api_client: TestClient):
        for node in api_client.get("/compilations").json():
            response = api_client.get(f"/compilations/{node['slug']}")
            assert response.status_code == 200

            detail = response.json()
            assert detail["source_id"] == node["source_id"]
            assert len(detail["members"]) == node["n_members"]
            # `parent_ids` and `parents` are the same edges, two shapes.
            # (Different orderings: ids ascend, parents read by slug.)
            assert sorted(p["source_id"] for p in detail["parents"]) == sorted(
                node["parent_ids"]
            )

    def test_detail_accepts_a_source_id(self, api_client: TestClient):
        source_id = api_client.get(f"/compilations/{TEST_SOURCE_TABLE.slug}").json()[
            "source_id"
        ]

        response = api_client.get(f"/compilations/{source_id}")
        assert response.status_code == 200
        assert response.json()["slug"] == TEST_SOURCE_TABLE.slug

    def test_detail_of_an_ordinary_map(self, api_client: TestClient):
        """Any map is addressable -- the route answers "where does this sit?" too."""
        response = api_client.get(f"/compilations/{TEST_SOURCE_TABLE.slug}")
        assert response.status_code == 200

        detail = response.json()
        assert detail["members"] == []
        assert not detail["is_compilation"]

    def test_unknown_map(self, api_client: TestClient):
        assert api_client.get("/compilations/not-a-real-map").status_code == 404


class TestLocationFilter:
    """`lng`/`lat` prune the graph to the compilations covering a point."""

    def test_half_a_location_is_refused(self, api_client: TestClient):
        assert api_client.get("/compilations?lng=-90").status_code == 400
        assert api_client.get("/compilations?lat=43").status_code == 400

    def test_open_ocean_covers_nothing(self, api_client: TestClient):
        # 0°N 0°E is in the Gulf of Guinea; no map footprint reaches it.
        response = api_client.get("/compilations?lng=0&lat=0")
        assert response.status_code == 200
        assert response.json() == []

    def test_filtered_is_a_subset_and_closed_upward(self, api_client: TestClient):
        everything = api_client.get("/compilations").json()
        by_id = {d["source_id"]: d for d in everything}

        for lng, lat in [(-123.0, 53.5), (-90.0, 43.0), (10.0, 46.0)]:
            here = api_client.get(f"/compilations?lng={lng}&lat={lat}").json()
            ids = {d["source_id"] for d in here}
            assert ids <= set(by_id)

            # A compilation's leaves are a superset of any member's, so anything
            # covering the point drags its parents in with it. Without this the
            # filtered set would not assemble into a tree.
            for node in here:
                for parent in node["parent_ids"]:
                    assert parent in ids

    def test_members_are_pruned_but_counts_are_not(self, api_client: TestClient):
        for node in api_client.get("/compilations?lng=-90.0&lat=43.0").json():
            detail = api_client.get(
                f"/compilations/{node['slug']}?lng=-90.0&lat=43.0"
            ).json()

            # The denominator survives the filter, so a client can say
            # "1 of 249 members here".
            assert detail["n_members"] == node["n_members"]
            assert len(detail["members"]) <= detail["n_members"]
            # Anything covering the point has at least one member that does.
            assert len(detail["members"]) > 0


class TestGraph:
    """`/compilations/graph` — the whole hierarchy in one payload."""

    def test_graph_is_the_same_facts_as_the_index(self, api_client: TestClient):
        graph = api_client.get("/compilations/graph").json()
        index = api_client.get("/compilations").json()

        nodes = {n["source_id"]: n for n in graph["nodes"]}
        # Every compilation in the index is a node of the graph, agreeing on the
        # facts both report. One vocabulary, two shapes.
        for node in index:
            assert node["source_id"] in nodes
            graph_node = nodes[node["source_id"]]
            for key in ("slug", "n_members", "n_sources", "state", "content"):
                assert graph_node[key] == node[key]

    def test_every_edge_endpoint_is_a_node(self, api_client: TestClient):
        graph = api_client.get("/compilations/graph").json()
        ids = {n["source_id"] for n in graph["nodes"]}

        for edge in graph["edges"]:
            assert edge["compilation_id"] in ids
            assert edge["member_id"] in ids

    def test_graph_holds_the_leaf_maps_too(self, api_client: TestClient):
        """The point of one payload: the maps at the bottom, not just the
        compilations, so a client never needs a request per level."""
        graph = api_client.get("/compilations/graph").json()
        if len(graph["edges"]) == 0:
            return
        assert any(not n["is_compilation"] for n in graph["nodes"])

    def test_location_prunes_both_sides(self, api_client: TestClient):
        everything = api_client.get("/compilations/graph").json()
        here = api_client.get("/compilations/graph?lng=-90.0&lat=43.0").json()

        all_ids = {n["source_id"] for n in everything["nodes"]}
        ids = {n["source_id"] for n in here["nodes"]}
        assert ids <= all_ids

        # Edges are pruned with the nodes, so the filtered graph is still a
        # graph rather than one with dangling endpoints.
        for edge in here["edges"]:
            assert edge["compilation_id"] in ids
            assert edge["member_id"] in ids

    def test_open_ocean_is_an_empty_graph(self, api_client: TestClient):
        graph = api_client.get("/compilations/graph?lng=0&lat=0").json()
        assert graph == {"nodes": [], "edges": []}

    def test_standalone_maps_are_in_no_edge(self, api_client: TestClient):
        """Ingested maps nothing has wrapped. They are in the graph so a client
        can show them as a fallback rather than silently omitting them."""
        graph = api_client.get("/compilations/graph").json()
        linked = {e["compilation_id"] for e in graph["edges"]} | {
            e["member_id"] for e in graph["edges"]
        }

        for node in graph["nodes"]:
            # The flag is exactly "appears in no edge" — the two must not drift.
            assert node["is_standalone"] == (node["source_id"] not in linked)
            if node["is_standalone"]:
                # Only *ingested* maps qualify; a bare `maps.sources` row with
                # neither polygons nor a footprint would bury the real ones.
                assert node["holds_polygons"] or node["area_km"] is not None


class TestNeighbors:
    """`/compilations/{ident}/neighbors` — other maps covering the same ground."""

    def test_unknown_map(self, api_client: TestClient):
        assert (
            api_client.get("/compilations/not-a-real-map/neighbors").status_code == 404
        )

    def test_a_map_is_not_its_own_neighbour(self, api_client: TestClient):
        result = api_client.get(
            f"/compilations/{TEST_SOURCE_TABLE.slug}/neighbors"
        ).json()
        assert all(n["source_id"] != result["source_id"] for n in result["neighbors"])

    def test_bounded_and_grouped_by_scale(self, api_client: TestClient):
        result = api_client.get(
            f"/compilations/{TEST_SOURCE_TABLE.slug}/neighbors?limit=10"
        ).json()
        assert len(result["neighbors"]) <= 10

        # Peers first, then each finer band — a client groups on consecutive
        # runs, so the ordering has to be monotonic in scale distance.
        distances = [n["scale_distance"] for n in result["neighbors"]]
        assert distances == sorted(distances)

        for group in {d for d in distances}:
            fractions = [
                n["overlap_fraction"]
                for n in result["neighbors"]
                if n["scale_distance"] == group and n["overlap_fraction"] is not None
            ]
            # Within a band, most of this map covered first.
            assert fractions == sorted(fractions, reverse=True)
            # A footprint cannot overlap more of this map than the whole of it.
            assert all(0 <= f <= 1.0000001 for f in fractions)

    def test_coarser_maps_are_excluded_by_default(self, api_client: TestClient):
        """The point of the scale filter: the same global sheets otherwise head
        every map's list."""
        slug = TEST_SOURCE_TABLE.slug
        default = api_client.get(f"/compilations/{slug}/neighbors?limit=200").json()
        assert default["include_coarser"] is False
        assert all(n["scale_distance"] >= 0 for n in default["neighbors"])

        widened = api_client.get(
            f"/compilations/{slug}/neighbors?limit=200&include_coarser=true"
        ).json()
        assert widened["include_coarser"] is True
        kept = {n["source_id"] for n in default["neighbors"]}
        assert kept <= {n["source_id"] for n in widened["neighbors"]}
        # Coarser maps sort after the peers and the finer bands: they are
        # context, not the answer.
        distances = [n["scale_distance"] for n in widened["neighbors"]]
        positive = [d for d in distances if d >= 0]
        assert distances[: len(positive)] == positive

    def test_own_compilations_are_not_neighbours(self, api_client: TestClient):
        """A map's own compilation covers all of it by construction. That is a
        membership fact, not another map of the area."""
        slug = TEST_SOURCE_TABLE.slug
        detail = api_client.get(f"/compilations/{slug}").json()
        parents = {p["source_id"] for p in detail["parents"]}

        result = api_client.get(
            f"/compilations/{slug}/neighbors?limit=200&include_coarser=true"
        ).json()
        assert parents.isdisjoint({n["source_id"] for n in result["neighbors"]})

    def test_overlap_is_null_exactly_when_unavailable(self, api_client: TestClient):
        """The flag and the values must agree — a null overlap with the flag set
        would read as "no overlap" rather than "not measured"."""
        for slug in [TEST_SOURCE_TABLE.slug]:
            result = api_client.get(f"/compilations/{slug}/neighbors").json()
            if result["overlap_available"]:
                assert all(n["overlap_km"] is not None for n in result["neighbors"])
            else:
                assert all(n["overlap_km"] is None for n in result["neighbors"])
