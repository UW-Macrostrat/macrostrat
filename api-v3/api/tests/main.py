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
from api.models import PolygonModel

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


class TestModels:

  def test_polygon_model(self):
    x = PolygonModel.model_validate({'descrip': 'TEst'})


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


  def test_get_sources_tables_default(self, api_client: TestClient):
    response = api_client.get(f"/sources/1/polygons?strat_name=group_by&page=0&page_size=999999")
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

  def test_get_source_tables_with_filter_in(self, api_client):

    db_ids = [*range(1,11)]
    db_id_str = f"({','.join(map(str, db_ids))})"

    response = api_client.get(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      params={"_pkid": f"in.{db_id_str}"},
    )

    assert response.status_code == 200

    response_json = response.json()

    assert all([x["_pkid"] in db_ids for x in response_json])


  def test_patch_source_tables_with_filter_in(self, api_client):
    def test_patch_source_tables_with_filter(self, api_client):
      id_temp_value = random.randint(1, 999)

      response = api_client.patch(
        f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
        json={
          TEST_SOURCE_TABLE.to_patch: id_temp_value
        },
        params=TEST_SOURCE_TABLE.to_filter
      )

      assert response.status_code == 204

      response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params=TEST_SOURCE_TABLE.to_filter)

      assert response.status_code == 200
      response_json = response.json()

      selected_values = filter(lambda x: x["PTYPE"] == "Qff", response_json)

      assert all([x["orig_id"] == id_temp_value for x in selected_values])


  def test_patch_source_tables_with_filter(self, api_client):

    body = {"descrip": "Test"}
    params = {"_pkid": "in.(1)"}


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
      json={TEST_SOURCE_TABLE.to_patch: id_temp_value},
      params={"PTYPE": "eq.Qff", "orig_id": "eq.999999"}
    )

    assert response.status_code == 400

    response_json = response.json()

    assert response_json["detail"] == "No rows patched, if this is unexpected please report as bug"

  def test_group_by_source_table(self, api_client):
    group_response = api_client.get(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      params={"PTYPE": "group_by"}
    )

    assert group_response.status_code == 200

    group_data = group_response.json()
    comparison_values = {r['PTYPE']: r['_pkid'] for r in group_data}

    assert len(group_data) > 0

    full_response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons")
    assert full_response.status_code == 200
    full_data = full_response.json()

    for row in full_data:
      assert str(row["_pkid"]) in comparison_values[row["PTYPE"]]


  def test_order_by_source_table(self, api_client):
    order_response = api_client.get(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      params={"_pkid": "order_by"}
    )

    assert order_response.status_code == 200

    order_data = order_response.json()

    assert len(order_data) > 0

    assert all([order_data[i]["_pkid"] <= order_data[i+1]["_pkid"] for i in range(len(order_data)-1)])



