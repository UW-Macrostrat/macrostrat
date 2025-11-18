from fastapi import FastAPI
from fastapi.testclient import TestClient

from . import router

test_app = FastAPI()
test_app.include_router(router)

client = TestClient(test_app)


def test_match_units_no_params():
    response = client.get("/strat-names")
    assert response.status_code == 422  # Missing required parameters
    data = response.json()
    assert "detail" in data
