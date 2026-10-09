"""The tile servers' `/version` and `/health` routes. Database-free, with a stand-in pool."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from macrostrat.tileserver_utils import status_router


class Pool:
    def __init__(self, fails=False):
        self.fails = fails

    @asynccontextmanager
    async def acquire(self, timeout=None):
        if self.fails:
            raise ConnectionError("database is down")
        yield self

    async def fetchval(self, query, timeout=None):
        return 1


def client(pool):
    app = FastAPI()
    app.include_router(status_router("tileserver"))
    app.state.pool = pool
    return TestClient(app)


def test_version_reports_the_build(monkeypatch):
    monkeypatch.setenv("MACROSTRAT_VERSION", "3.2.0")
    monkeypatch.setenv("MACROSTRAT_RELEASE", "true")
    monkeypatch.setenv("MACROSTRAT_COMMIT", "abc123")
    monkeypatch.setenv("MACROSTRAT_BUILD_DATE", "2026-10-09T12:00:00.000Z")
    monkeypatch.setenv("MACROSTRAT_REPOSITORY", "UW-Macrostrat/macrostrat")
    res = client(Pool()).get("/version")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    assert res.json() == {
        "service": "tileserver",
        "version": "3.2.0",
        "release": True,
        "commit": "abc123",
        "build_date": "2026-10-09T12:00:00.000Z",
        "repository": "UW-Macrostrat/macrostrat",
    }


def test_local_build_reports_nulls(monkeypatch):
    # Docker sets an unpassed build argument to an empty string
    for key in ["VERSION", "RELEASE", "COMMIT", "BUILD_DATE", "REPOSITORY"]:
        monkeypatch.setenv(f"MACROSTRAT_{key}", "")
    info = client(Pool()).get("/version").json()
    assert info["version"] is None
    assert info["commit"] is None
    assert info["release"] is False


def test_health_ok():
    res = client(Pool()).get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_unavailable_without_database():
    res = client(Pool(fails=True)).get("/health")
    assert res.status_code == 503
    assert res.headers["cache-control"] == "no-store"


def test_health_unavailable_before_pool_exists():
    app = FastAPI()
    app.include_router(status_router("tileserver"))
    assert TestClient(app).get("/health").status_code == 503
