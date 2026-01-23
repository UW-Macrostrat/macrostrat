import datetime
import hashlib
import os
import random

import pytest

# Have to run before the imports that use the db env variables
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

load_dotenv()

import api.database as db
from api.app import app
from api.database import connect_engine, dispose_engine, get_engine
from api.models.geometries import PolygonModel

# Define some testing values

UNUSED_SOURCE_ID = 9999


class TEST_SOURCE_TABLE:
    source_id = 898
    slug = "guam"
    to_patch = "orig_id"
    to_filter = {"PTYPE": "eq.Qff"}


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    headers = {}
    test_token = os.environ.get("TEST_ACCESS_TOKEN")
    if test_token:
        headers["access_token"] = f"Bearer {test_token}"

    with TestClient(app, headers=headers) as client:
        yield client


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
        x = PolygonModel.model_validate({"descrip": "TEst"})


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

        result = await db.insert_access_token(
            engine,
            token=test_value,
            group_id=1,
            expiration=datetime.datetime.fromtimestamp(1),
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_schema_tables(self, engine: AsyncEngine):
        result = await db.get_schema_tables(engine=engine, schema="sources")

        results = [*result]

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_patch_sources_sub_table_set_columns_equal(self, engine: AsyncEngine):
        test_value = f"test-{random.randint(0, 10000000)}"

        await db.patch_sources_sub_table(
            engine=engine,
            table_id=TEST_SOURCE_TABLE.source_id,
            update_values={"comments": test_value},
            query_params=[],
        )

        await db.patch_sources_sub_table_set_columns_equal(
            engine=engine,
            table_id=TEST_SOURCE_TABLE.source_id,
            target_column="descrip",
            source_column="comments",
            query_params=[],
        )

        result = await db.select_sources_sub_table(
            table_id=TEST_SOURCE_TABLE.source_id, engine=engine, query_params=[]
        )

        assert all([x["descrip"] == test_value for x in result.to_dict()])
