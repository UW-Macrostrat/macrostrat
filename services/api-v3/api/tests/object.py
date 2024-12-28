import random
import hashlib
import os

from .main import api_client

class TestObjectCRUD:

    def test_object_post(self, api_client):
        """Test posting an object to the database"""

        key = f"test-{random.randint(0, 10000000)}"

        object_data = {
            "scheme": "http",
            "host": "test.com",
            "bucket": "test",
            "key": key,
            "source": {
                "test_key": "test_value"
            },
            "mime_type": "application/json",
            "sha256_hash": hashlib.sha256(open(__file__, "rb").read()).hexdigest()
        }

        response = api_client.post(
            "/object",
            json=object_data,
        )

        assert response.status_code == 200

    def test_object_file_post(self, api_client):
        """Test posting an object to the database"""

        random_string = f"test-{random.randint(0, 10000000)}"

        response = api_client.post(
            "/object",
            files=[
                ("object", ("test.txt", open(f"./tests/data/{random_string}.txt", "rb"), "text/plain"))
            ]
        )

        assert response.status_code == 200

    def test_object_multi_file_post(self, api_client):
        """Test posting an object to the database"""

        response = api_client.post(
            "/object",
            files=[
                ("object", ("test.txt", open("./tests/data/test.txt", "rb"), "text/plain")),
                ("object", ("object.py", open("./tests/object.py", "rb"), "text/plain"))
            ]
        )

        assert response.status_code == 200

    def test_object_post_to_ingest_process(self, api_client):
        """Test posting an object to the database and associating it with an ingest process"""

        response = api_client.post(
            "/ingest-process/1/objects",
            files={"object": open("./tests/data/test.txt", "rb")}
        )

        assert response.status_code == 200

    def test_object_multi_file_post_to_ingest_process(self, api_client):
        """Test posting an object to the database"""

        random_string = f"test-{random.randint(0, 10000000)}"

        response = api_client.post(
            "/ingest-process/1/objects",
            files=[
                ("object", (f"{random_string}.txt", open("./tests/data/test.txt", "rb"), "text/plain")),
                ("object", (f"{random_string}.py", open("./tests/object.py", "rb"), "text/plain"))
            ]
        )

        assert response.status_code == 200

    def test_get_objects(self, api_client):
        response = api_client.get("/object")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

    def test_get_object(self, api_client):
        response = api_client.get("/object")
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.get(f"/object/{data[0]['id']}")

        assert response.status_code == 200

        single_data = response.json()

        assert single_data == data[0]

    def test_patch_object(self, api_client):
        # Get a object
        response = api_client.get("/object")
        assert response.status_code == 200
        object_data = response.json()
        assert len(object_data) > 0

        # Patch Object
        response = api_client.patch(
            f"/object/{object_data[0]['id']}",
            json={
                "source": {
                    "comments": "test"
                }
            }
        )
        assert response.status_code == 200
        single_data = response.json()

        assert single_data['source']['comments'] == "test"

    def test_delete_object(self, api_client):
        key = f"test-{random.randint(0, 10000000)}"

        object_data = {
            "scheme": "http",
            "host": "test.com",
            "bucket": "test",
            "key": key,
            "source": {
                "test_key": "test_value"
            },
            "mime_type": "application/json",
            "sha256_hash": hashlib.sha256(open(__file__, "rb").read()).hexdigest()
        }

        response = api_client.post("/object", json=object_data)
        assert response.status_code == 200

        data = response.json()

        assert len(data) > 0

        response = api_client.delete(f"/object/{data['id']}")
        assert response.status_code == 200

        response = api_client.get(f"/object/{data['id']}")
        assert response.status_code == 404
