import random

from .test_database import api_client


class TestIngestProcess:
    """Test the ingest process; Warning: These do not clean up after themselves"""

    def test_add_ingest_process(self, api_client):
        """Test adding an ingest process"""

        ingest_process_data = {"comments": "This is a test comment", "state": "pending"}

        response = api_client.post(
            "/ingest-process",
            json=ingest_process_data,
        )

        assert response.status_code == 200

        data = response.json()

        assert data["comments"] == "This is a test comment"
        assert data["state"] == "pending"
        assert data["tags"] == []

    def test_add_ingest_process_with_tags(self, api_client):
        """Test adding an ingest process"""

        ingest_process_data = {
            "comments": "This is a test comment",
            "state": "pending",
            "tags": ["delete me"],
        }

        response = api_client.post(
            "/ingest-process",
            json=ingest_process_data,
        )

        assert response.status_code == 200

        data = response.json()

        assert data["comments"] == "This is a test comment"
        assert data["state"] == "pending"
        assert data["tags"] == ["delete me"]

    def test_get_ingest_processes(self, api_client):
        response = api_client.get("/ingest-process?tags=eq.delete+me")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

    def test_get_ingest_process_tags(self, api_client):
        """Test getting tags for an ingest process"""

        response = api_client.get("/ingest-process/tags")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_get_ingest_process(self, api_client):
        response = api_client.get("/ingest-process")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.get(f"/ingest-process/{data[0]['id']}")

        assert response.status_code == 200

        single_data = response.json()

        assert single_data == data[0]

    def test_patch_ingest_process(self, api_client):
        response = api_client.get("/ingest-process")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.patch(
            f"/ingest-process/{data[0]['id']}", json={"comments": "test"}
        )

        assert response.status_code == 200

        single_data = response.json()

        assert single_data["comments"] == "test"

    def test_add_tag_to_ingest_process(self, api_client):
        """Test adding a tag to an ingest process"""

        test_tag = f"new_tag-{random.randint(0, 10000000)}"

        response = api_client.get("/ingest-process")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.post(
            f"/ingest-process/{data[0]['id']}/tags", json={"tag": test_tag}
        )

        assert response.status_code == 200

        single_data = response.json()

        assert test_tag in single_data

    def test_delete_tag_from_ingest_process(self, api_client):
        """Test deleting a tag from an ingest process"""

        test_tag = f"new_tag-{random.randint(0, 10000000)}"

        response = api_client.get("/ingest-process")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.post(
            f"/ingest-process/{data[0]['id']}/tags", json={"tag": test_tag}
        )
        post_data = response.json()

        assert response.status_code == 200
        assert test_tag in post_data

        response = api_client.delete(f"/ingest-process/{data[0]['id']}/tags/{test_tag}")

        assert response.status_code == 200

        single_data = response.json()

        assert test_tag not in single_data

    def test_pair_object_to_ingest(self, api_client):
        response = api_client.get("/ingest-process")
        assert response.status_code == 200
        ingest_data = response.json()[0]

        response = api_client.get("/object")
        assert response.status_code == 200
        object_data = response.json()[0]

        # Pair the object to the ingest process
        response = api_client.patch(
            f"/object/{object_data['id']}",
            json={"object_group_id": ingest_data["object_group_id"]},
        )
        assert response.status_code == 200

    def test_get_objects(self, api_client):

        # Add an ingest process
        ingest_process_data = {"comments": "This is a test comment", "state": "pending"}
        ingest_response = api_client.post(
            "/ingest-process",
            json=ingest_process_data,
        )
        assert ingest_response.status_code == 200
        ingest_data = ingest_response.json()

        # Add some objects
        keys = []
        for i in range(4):
            key = f"test-{random.randint(0, 10000000)}"
            keys.append(key)
            object_data = {
                "scheme": "http",
                "host": "test.com",
                "bucket": "test",
                "key": key,
                "source": {"test_key": "test_value"},
                "mime_type": "application/json",
            }
            response = api_client.post("/object", json=object_data)
            assert response.status_code == 200
            object_data = response.json()

            # Pair the object to the ingest process
            response = api_client.patch(
                f"/object/{object_data['id']}",
                json={"object_group_id": ingest_data["object_group_id"]},
            )
            assert response.status_code == 200

        response = api_client.get(f"/ingest-process/{ingest_data['id']}/objects")
        assert response.status_code == 200
        objects = response.json()

        assert len(objects) == 4
        for object in objects:
            assert object["key"] in keys

    # @pytest.skip("Manual testing only")
    def test_get_objects_known_ingest_process(self, api_client):

        ingest_process_id = 1

        response = api_client.get(f"/ingest-process/{ingest_process_id}/objects")
        assert response.status_code == 200
        objects = response.json()

        assert len(objects) > 0
        assert objects[0]["pre_signed_url"] is not None
