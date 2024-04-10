import pytest
import os
import hashlib
import datetime
import random

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from fastapi.testclient import TestClient

# Have to run before the imports that use the db env variables
from dotenv import load_dotenv

load_dotenv()

from api.app import app
from api.database import connect_engine, dispose_engine, get_engine
import api.database as db
from api.models.geometries import PolygonModel

# Define some testing values

UNUSED_SOURCE_ID = 9999


class TEST_SOURCE_TABLE:
    source_id = 898
    slug = "guam"
    to_patch = "orig_id"
    to_filter = {
        "PTYPE": "eq.Qff"
    }


@pytest.fixture
def api_client() -> TestClient:
    with TestClient(app) as api_client:
        yield api_client


@pytest.fixture
async def engine() -> AsyncEngine:
    await connect_engine()
    yield get_engine()
    await dispose_engine()


@pytest.fixture
async def session(engine: AsyncEngine):
    async_session = async_sessionmaker(engine)
    yield async_session


class TestModels:

    def test_polygon_model(self):
        x = PolygonModel.model_validate({
                                            'descrip': 'TEst'
                                        })


class TestUtils:

    @pytest.mark.asyncio
    async def test_source_id_to_slug(self, engine: AsyncEngine):
        slug = await db.source_id_to_slug(engine, TEST_SOURCE_TABLE.source_id)
        assert slug == TEST_SOURCE_TABLE.slug


class TestSessionDB:

    @pytest.mark.asyncio
    async def test_get_sources_table(self, session: async_sessionmaker[AsyncSession]):
        sources = await db.get_sources(session)
        assert len(sources) > 0


class TestEngineDB:

    @pytest.mark.asyncio
    async def test_token_insert(self, engine: AsyncEngine):
        test_value = f"test-{random.randint(0, 10000000)}"

        result = await db.insert_access_token(engine, token=test_value, group_id=1,
                                              expiration=datetime.datetime.fromtimestamp(1))

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_schema_tables(self, engine: AsyncEngine):
        result = await db.get_schema_tables(engine=engine, schema="sources")

        results = [*result]

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_patch_sources_sub_table_set_columns_equal(self, engine: AsyncEngine):
        test_value = f"test-{random.randint(0, 10000000)}"

        await db.patch_sources_sub_table(engine=engine, table_id=TEST_SOURCE_TABLE.source_id, update_values={
            "comments": test_value
        }, query_params=[])

        await db.patch_sources_sub_table_set_columns_equal(
            engine=engine,
            table_id=TEST_SOURCE_TABLE.source_id,
            target_column="descrip",
            source_column="comments",
            query_params=[]
        )

        result = await db.select_sources_sub_table(table_id=TEST_SOURCE_TABLE.source_id, engine=engine, query_params=[])

        assert all([x["descrip"] == test_value for x in result.to_dict()])


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
