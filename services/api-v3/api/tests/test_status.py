"""`/version` and `/health`. Database-free, with a stand-in for the app database."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_database
from api.routes.status import router


class Database:
    def __init__(self, fails=False):
        self.fails = fails

    @asynccontextmanager
    async def async_connection(self):
        if self.fails:
            raise ConnectionError("database is down")
        yield self

    async def execute(self, statement):
        return None


def client(database):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: database
    return TestClient(app)


def test_version_reports_the_build(monkeypatch):
    monkeypatch.setenv("MACROSTRAT_VERSION", "3.0.0-beta.1")
    monkeypatch.setenv("MACROSTRAT_RELEASE", "")
    monkeypatch.setenv("MACROSTRAT_COMMIT", "abc123")
    res = client(Database()).get("/version")
    assert res.headers["cache-control"] == "no-store"
    info = res.json()
    assert info["service"] == "api-v3"
    assert info["version"] == "3.0.0-beta.1"
    assert info["release"] is False
    assert info["commit"] == "abc123"


def test_health_ok():
    res = client(Database()).get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_unavailable_without_database():
    assert client(Database(fails=True)).get("/health").status_code == 503
