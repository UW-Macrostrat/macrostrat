import pytest
import os
import json

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
import random

from fastapi.testclient import TestClient


# Have to run before the imports that use the db env variables
from dotenv import load_dotenv
load_dotenv()

from api.app import app
from api.database import connect_engine, dispose_engine, get_engine
import api.database as db

# Define some testing values

UNUSED_SOURCE_ID=9999

class TEST_SOURCE_TABLE:
  source_id=295
  primary_table="test_id"
  to_patch = "orig_id"
  to_filter = {"PTYPE": "eq.Qff"}

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


class TestUtils:

  @pytest.mark.asyncio
  async def test_source_id_to_primary_table(self, session: async_sessionmaker[AsyncSession]):
    primary_table = await db.source_id_to_primary_table(session, TEST_SOURCE_TABLE.source_id)
    assert primary_table == TEST_SOURCE_TABLE.primary_table

  @pytest.mark.asyncio
  async def test_source_id_to_primary_table(self, session: async_sessionmaker[AsyncSession]):
    with pytest.raises(NoResultFound) as e_info:
      await db.source_id_to_primary_table(session, UNUSED_SOURCE_ID)


class TestSessionDB:

  @pytest.mark.asyncio
  async def test_get_sources_table(self, session: async_sessionmaker[AsyncSession]):
    sources = await db.get_sources(session)
    assert len(sources) > 0


class TestEngineDB:

  @pytest.mark.asyncio
  async def test_get_schema_tables(self, engine: AsyncEngine):
    result = await db.get_schema_tables(engine=engine, schema="sources")

    results = [*result]

    assert len(results) > 0


class TestAPI:

  def test_get_sources(self, api_client: TestClient):
    response = api_client.get("/sources")
    assert response.status_code == 200


  def test_get_sources_tables(self, api_client: TestClient):
    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")
    assert response.status_code == 200
    response_json = response.json()

    assert len(response_json) > 0


  def test_get_source_tables_filtered(self, api_client: TestClient):
    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params={"PTYPE": "eq.Qff"})

    assert response.status_code == 200
    response_json = response.json()

    assert len(response_json) > 0

  def test_patch_source_tables(self, api_client):

    id_temp_value = random.randint(1, 999)

    response = api_client.patch(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", json={TEST_SOURCE_TABLE.to_patch: id_temp_value})

    assert response.status_code == 204

    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")

    assert response.status_code == 200
    response_json = response.json()

    assert all([x["orig_id"] == id_temp_value for x in response_json])


  def test_patch_source_tables_with_filter(self, api_client):

    id_temp_value = random.randint(1, 999)

    response = api_client.patch(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      json={TEST_SOURCE_TABLE.to_patch: id_temp_value},
      params=TEST_SOURCE_TABLE.to_filter
    )

    assert response.status_code == 204

    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params=TEST_SOURCE_TABLE.to_filter)

    assert response.status_code == 200
    response_json = response.json()

    selected_values = filter(lambda x: x["PTYPE"] == "Qff", response_json)

    assert all([x["orig_id"] == id_temp_value for x in selected_values])



