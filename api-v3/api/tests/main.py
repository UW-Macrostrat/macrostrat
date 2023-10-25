import pytest
import os
import json

from sqlalchemy.ext.asyncio import AsyncEngine


from fastapi.testclient import TestClient


# Have to run before the imports that use the db env variables
from dotenv import load_dotenv
load_dotenv()

from api.app import app
from api.database import connect_engine, dispose_engine, get_engine
import api.database as db

TEST_POLYGON_TABLE="ab_spray"

@pytest.fixture
def api_client() -> TestClient:
  with TestClient(app) as api_client:
    yield api_client

@pytest.fixture
async def engine() -> AsyncEngine:
  await connect_engine()
  yield get_engine()
  await dispose_engine()


class TestDB:

  @pytest.mark.asyncio
  async def test_get_schema_tables(self, engine: AsyncEngine):
    result = await db.get_schema_tables(engine=engine, schema="sources")

    results = [*result]

    assert len(results) > 0




class TestAPI:

  def test_get_sources(self, api_client: TestClient):
    response = api_client.get(f"/sources/{TEST_POLYGON_TABLE}/polygons")
    assert response.status_code == 200
    response_json = response.json()

