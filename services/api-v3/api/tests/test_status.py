"""`/version`, `/workers/version` and `/health`, with stand-ins for the database and broker."""

from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_database
from api.routes import status
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


class Broker:
    """Celery's app, connection and control in one, as the route uses them."""

    def __init__(self, replies=(), down=False):
        self.replies = list(replies)
        self.down = down
        self.control = self

    @contextmanager
    def connection_for_write(self):
        yield self

    def ensure_connection(self, timeout=None):
        if self.down:
            raise ConnectionError("broker is down")

    def broadcast(self, command, **kwargs):
        assert command == "build"
        return self.replies


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


def test_worker_version_lists_each_worker(monkeypatch):
    admin = {"service": "worker", "version": "1.2.0", "queues": ["admin"]}
    maps = {"service": "worker", "version": "1.1.1", "queues": ["columns", "maps"]}
    old = {"error": "No such command"}
    replies = [{"celery@admin": admin}, {"celery@maps": maps}, {"celery@old": old}]
    monkeypatch.setattr(status, "celery_app", Broker(replies))
    res = client(Database()).get("/workers/version")
    assert res.headers["cache-control"] == "no-store"
    assert res.json() == [old, admin, maps]


def test_worker_version_unavailable_without_broker(monkeypatch):
    monkeypatch.setattr(status, "celery_app", Broker(down=True))
    assert client(Database()).get("/workers/version").status_code == 503
