import random

from fastapi.testclient import TestClient

from .main import TEST_SOURCE_TABLE, api_client


class TestAPI:

    def test_get_sources(self, api_client: TestClient):
        response = api_client.get("/sources")
        assert response.status_code == 200

    def test_get_source(self, api_client: TestClient):
        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}")
        assert response.status_code == 200

        response_json = response.json()

        assert response_json["source_id"] == TEST_SOURCE_TABLE.source_id

    def test_patch_source(self, api_client: TestClient):

    def test_get_sub_source_geometries(self, api_client: TestClient):
        response = api_client.get(f"/sources/{1}/geometries")
        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_get_sources_polygons_table(self, api_client: TestClient):
        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")
        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_get_sources_points_table(self, api_client: TestClient):
        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/points")
        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_get_source_linestrings_table(self, api_client: TestClient):
        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/linestrings")
        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_get_sources_tables_default(self, api_client: TestClient):
        response = api_client.get(f"/sources/1/polygons?strat_name=group_by&page=0&page_size=999999")
        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_get_source_tables_filtered(self, api_client: TestClient):
        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params={
            "PTYPE": "eq.Qff"
        })

        assert response.status_code == 200
        response_json = response.json()

        assert len(response_json) > 0

    def test_patch_source_tables(self, api_client):
        id_temp_value = random.randint(1, 999)

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            json={
                TEST_SOURCE_TABLE.to_patch: id_temp_value
            }
        )

        assert response.status_code == 204

        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")

        assert response.status_code == 200
        response_json = response.json()

        assert all([x["orig_id"] == id_temp_value for x in response_json])

    def test_get_source_tables_with_filter_in(self, api_client):
        db_ids = [*range(1, 11)]
        db_id_str = f"({','.join(map(str, db_ids))})"

        response = api_client.get(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            params={
                "_pkid": f"in.{db_id_str}"
            },
        )

        assert response.status_code == 200

        response_json = response.json()

        assert all([x["_pkid"] in db_ids for x in response_json])

    def test_patch_source_tables_with_filter_in(self, api_client):
        id_temp_value = random.randint(1, 999)

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            json={
                TEST_SOURCE_TABLE.to_patch: id_temp_value
            },
            params=TEST_SOURCE_TABLE.to_filter
        )

        assert response.status_code == 204

        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
                                  params=TEST_SOURCE_TABLE.to_filter)

        assert response.status_code == 200
        response_json = response.json()

        selected_values = filter(lambda x: x["PTYPE"] == "Qff", response_json)

        assert all([x["orig_id"] == id_temp_value for x in selected_values])

    def test_patch_source_tables_with_filter(self, api_client):
        body = {
            "descrip": "Test"
        }
        params = {
            "_pkid": "in.(1)"
        }

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            json=body,
            params=params
        )

        assert response.status_code == 204

        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params=params)

        assert response.status_code == 200
        response_json = response.json()

        selected_values = filter(lambda x: x["_pkid"] == 1, response_json)

        assert all([x["descrip"] == "Test" for x in selected_values])

    def test_patch_source_tables_with_filter_no_matches(self, api_client):
        id_temp_value = random.randint(1, 999)

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            json={
                TEST_SOURCE_TABLE.to_patch: id_temp_value
            },
            params={
                "PTYPE": "eq.Qff",
                "orig_id": "eq.999999"
            }
        )

        assert response.status_code == 400

        response_json = response.json()

        assert response_json["detail"] == "No rows patched, if this is unexpected please report as bug"

    def test_group_by_source_table(self, api_client):
        group_response = api_client.get(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            params={
                "PTYPE": "group_by"
            }
        )

        assert group_response.status_code == 200

        group_data = group_response.json()
        comparison_values = {r['PTYPE']: r['_pkid'] for r in group_data}

        assert len(group_data) > 0

        full_response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")
        assert full_response.status_code == 200
        full_data = full_response.json()

        for row in full_data:
            assert str(row["_pkid"]) in comparison_values[row["PTYPE"]] or comparison_values[
                row["PTYPE"]] == "Multiple Values"

    def test_order_by_source_table(self, api_client):
        order_response = api_client.get(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            params={
                "_pkid": "order_by"
            }
        )

        assert order_response.status_code == 200

        order_data = order_response.json()

        assert len(order_data) > 0

        assert all([order_data[i]["_pkid"] <= order_data[i + 1]["_pkid"] for i in range(len(order_data) - 1)])

    def test_copy_column_values(self, api_client):
        # First set all the 'descrip' values to a random value
        test_value = f"test-{random.randint(0, 10000000)}"

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
            json={
                "descrip": test_value
            }
        )

        assert response.status_code == 204

        response = api_client.patch(
            f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons/comments",
            json={
                "source_column": "descrip"
            }
        )

        assert response.status_code == 204

        response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")

        assert response.status_code == 200

        response_data = response.json()

        assert all([x["descrip"] == x["comments"] for x in response_data])
