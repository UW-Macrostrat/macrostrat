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

UNUSED_SOURCE_ID=9999

class TEST_SOURCE_TABLE:
  source_id=898
  slug="guam"
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

    test_value = f"test-{random.randint(0,10000000)}"

    result = await db.insert_access_token(engine, token=test_value, group_id=1, expiration=datetime.datetime.fromtimestamp(1))

    assert result is not None

  @pytest.mark.asyncio
  async def test_get_schema_tables(self, engine: AsyncEngine):
    result = await db.get_schema_tables(engine=engine, schema="sources")

    results = [*result]

    assert len(results) > 0

  @pytest.mark.asyncio
  async def test_patch_sources_sub_table_set_columns_equal(self, engine: AsyncEngine):

    test_value = f"test-{random.randint(0,10000000)}"

    await db.patch_sources_sub_table(engine=engine, table_id=TEST_SOURCE_TABLE.source_id, update_values={"comments": test_value}, query_params=[])

    await db.patch_sources_sub_table_set_columns_equal(
      engine=engine,
      table_id=TEST_SOURCE_TABLE.source_id,
      target_column="descrip",
      source_column="comments",
      query_params=[]
    )

    result = await db.select_sources_sub_table(table_id=TEST_SOURCE_TABLE.source_id, engine=engine, query_params=[])

    assert all([x["descrip"] == test_value for x in result.to_dict()])


class TestAPI:

  def test_get_sources(self, api_client: TestClient):
    response = api_client.get("/sources")
    assert response.status_code == 200


  def test_get_source(self, api_client: TestClient):
    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}")
    assert response.status_code == 200

    response_json = response.json()

    assert response_json["source_id"] == TEST_SOURCE_TABLE.source_id

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
    response = api_client.get(f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons", params={"PTYPE": "eq.Qff"})

    assert response.status_code == 200
    response_json = response.json()

    assert len(response_json) > 0


  def test_patch_source_tables(self, api_client):

    id_temp_value = random.randint(1, 999)

    response = api_client.patch(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      json={TEST_SOURCE_TABLE.to_patch: id_temp_value}
    )

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
      assert str(row["_pkid"]) in comparison_values[row["PTYPE"]] or comparison_values[row["PTYPE"]] == "Multiple Values"


  def test_order_by_source_table(self, api_client):
    order_response = api_client.get(
      f"/sources/{TEST_SOURCE_TABLE.source_id}/polygons",
      params={"_pkid": "order_by"}
    )

    assert order_response.status_code == 200

    order_data = order_response.json()

    assert len(order_data) > 0

    assert all([order_data[i]["_pkid"] <= order_data[i+1]["_pkid"] for i in range(len(order_data)-1)])


  def test_copy_column_values(self, api_client):

    # First set all the 'descrip' values to a random value
    test_value = f"test-{random.randint(0,10000000)}"

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

class TestObjectCRUD:

  def test_object_post(self, api_client):
    """Test posting an object to the database"""

    key = f"test-{random.randint(0,10000000)}"

    object_data = {
      "scheme": "http",
      "host": "test.com",
      "bucket": "test",
      "key": key,
      "source": {"test_key": "test_value"},
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
      json={"source": {"comments": "test"}}
    )
    assert response.status_code == 200
    single_data = response.json()

    assert single_data['source']['comments'] == "test"

  def test_delete_object(self, api_client):

    key = f"test-{random.randint(0,10000000)}"

    object_data = {
      "scheme": "http",
      "host": "test.com",
      "bucket": "test",
      "key": key,
      "source": {"test_key": "test_value"},
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


class TestIngestProcess:

  def test_add_ingest_process(self, api_client):
    """Test adding an ingest process"""

    ingest_process_data = {
      "comments": "This is a test comment",
      "state": "pending"
    }

    response = api_client.post(
      "/ingest-process",
      json=ingest_process_data,
    )

    assert response.status_code == 200

  def test_get_ingest_processes(self, api_client):
    response = api_client.get("/ingest-process")
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

    response = api_client.patch(f"/ingest-process/{data[0]['id']}", json={"comments": "test"})

    assert response.status_code == 200

    single_data = response.json()

    assert single_data['comments'] == "test"

  def test_pair_object_to_ingest(self, api_client):
    response = api_client.get("/ingest-process")
    assert response.status_code == 200
    ingest_data = response.json()[0]

    response = api_client.get("/object")
    assert response.status_code == 200
    object_data = response.json()[0]

    # Pair the object to the ingest process
    response = api_client.patch(f"/object/{object_data['id']}", json={"object_group_id": ingest_data['object_group_id']})
    assert response.status_code == 200

  def test_get_objects(self, api_client):

    # Add an ingest process
    ingest_process_data = {
      "comments": "This is a test comment",
      "state": "pending"
    }
    ingest_response = api_client.post(
      "/ingest-process",
      json=ingest_process_data,
    )
    assert ingest_response.status_code == 200
    ingest_data = ingest_response.json()

    # Add some objects
    keys = []
    for i in range(4):
      key = f"test-{random.randint(0,10000000)}"
      keys.append(key)
      object_data = {
        "scheme": "http",
        "host": "test.com",
        "bucket": "test",
        "key": key,
        "source": {"test_key": "test_value"},
        "mime_type": "application/json"
      }
      response = api_client.post("/object", json=object_data)
      assert response.status_code == 200
      object_data = response.json()

      # Pair the object to the ingest process
      response = api_client.patch(f"/object/{object_data['id']}", json={"object_group_id": ingest_data['object_group_id']})
      assert response.status_code == 200

    response = api_client.get(f"/ingest-process/{ingest_data['id']}/objects")
    assert response.status_code == 200
    objects = response.json()

    assert len(objects) == 4
    for object in objects:
      assert object['key'] in keys

  #@pytest.skip("Manual testing only")
  def test_get_objects_known_ingest_process(self, api_client):

    ingest_process_id = 1

    response = api_client.get(f"/ingest-process/{ingest_process_id}/objects")
    assert response.status_code == 200
    objects = response.json()

    assert len(objects) > 0
    assert objects[0]['pre_signed_url'] is not None
