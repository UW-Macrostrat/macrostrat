from __future__ import annotations

import json
import random
import string
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest

from .test_database import api_client


def test__debug_routes(api_client):
    paths = sorted({r.path for r in api_client.app.router.routes if hasattr(r, "path")})
    print("\n".join(paths))
    assert True


def _rand(prefix: str = "obj", n: int = 10) -> str:
    s = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))
    return f"{prefix}-{s}"


def _assert_list_shape(payload: Dict[str, Any]) -> None:
    assert isinstance(payload, dict)
    assert "items" in payload
    assert "next_before_id" in payload
    assert isinstance(payload["items"], list)


def _assert_object_row_shape(obj: Dict[str, Any]) -> None:
    # returned by SQL_INSERT_OBJECT / SQL_GET_OBJECT_BY_ID / SQL_PATCH_OBJECT
    for k in [
        "id",
        "scheme",
        "host",
        "bucket",
        "key",
        "sha256_hash",
        "mime_type",
        "source",
        "created_on",
        "updated_on",
    ]:
        assert k in obj

    assert obj["scheme"] == "s3"
    assert isinstance(obj["id"], int)
    assert isinstance(obj["key"], str)
    assert isinstance(obj["mime_type"], str)
    assert isinstance(obj["source"], (dict, str, type(None)))  # _row_to_dict tries to coerce


def _post_object_files(
    api_client, files: List[Tuple[str, Tuple[str, bytes, str]]]
):
    """
    POST /object expects multipart/form-data with one or many files under field name 'object'.

    files format for TestClient:
      files=[("object", ("name.txt", b"...", "text/plain")), ...]
    """
    return api_client.post("/object", files=files)


def _create_one(api_client, *, name: Optional[str] = None, content: bytes = b"hello") -> Dict[str, Any]:
    name = name or f"{_rand()}.txt"
    resp = _post_object_files(api_client, [("object", (name, content, "text/plain"))])
    assert resp.status_code == 200
    out = resp.json()
    assert "objects_created" in out
    assert isinstance(out["objects_created"], list)
    assert len(out["objects_created"]) in (0, 1)
    if len(out["objects_created"]) == 1:
        _assert_object_row_shape(out["objects_created"][0])
    return out


@dataclass
class CreatedObject:
    id: int
    key: str

@pytest.fixture(scope="module")
def object_registry(api_client):
    created: List[CreatedObject] = []
    yield created
    for obj in reversed(created):
        resp = api_client.delete(f"/object/{obj.id}?hard=true")
        assert resp.status_code == 200, (
            f"Cleanup hard delete failed for id={obj.id} key={obj.key}: {resp.text}"
        )

def _register_created(registry: List[CreatedObject], objects_created: List[Dict[str, Any]]) -> None:
    for o in objects_created:
        registry.append(CreatedObject(id=o["id"], key=o["key"]))


class TestObjectRoutes:
    def test_post_requires_multipart(self, api_client):
        # JSON should fail because route expects multipart/form-data
        resp = api_client.post("/object", json={"x": 1})
        assert resp.status_code == 400
        assert "multipart/form-data" in resp.json().get("detail", "")

    def test_post_requires_field_name_object(self, api_client):
        resp = api_client.post(
            "/object",
            files=[("not_object", ("a.txt", b"hi", "text/plain"))],
        )
        assert resp.status_code == 400
        assert "field name 'object'" in resp.json().get("detail", "")

    def test_post_single_file_creates_row(self, api_client, object_registry):
        name = f"{_rand()}.txt"
        resp = _post_object_files(api_client, [("object", (name, b"hello", "text/plain"))])
        assert resp.status_code == 200

        out = resp.json()
        assert "bucket" in out and "host" in out and "objects_created" in out
        assert len(out["objects_created"]) == 1

        obj = out["objects_created"][0]
        _assert_object_row_shape(obj)
        assert obj["key"] == name

        _register_created(object_registry, out["objects_created"])

    def test_post_multiple_files_creates_multiple(self, api_client, object_registry):
        n1 = f"{_rand()}.txt"
        n2 = f"{_rand()}.bin"
        resp = _post_object_files(
            api_client,
            [
                ("object", (n1, b"a" * 10, "text/plain")),
                ("object", (n2, b"\x00\x01\x02", "application/octet-stream")),
            ],
        )
        assert resp.status_code == 200
        out = resp.json()
        created = out["objects_created"]
        assert len(created) == 2
        keys = {o["key"] for o in created}
        assert keys == {n1, n2}

        _register_created(object_registry, created)

    def test_post_duplicate_key_skips(self, api_client, object_registry):
        name = f"{_rand()}.txt"

        r1 = _post_object_files(api_client, [("object", (name, b"first", "text/plain"))])
        assert r1.status_code == 200
        created1 = r1.json()["objects_created"]
        assert len(created1) == 1
        _register_created(object_registry, created1)

        r2 = _post_object_files(api_client, [("object", (name, b"second", "text/plain"))])
        assert r2.status_code == 200
        created2 = r2.json()["objects_created"]
        assert len(created2) == 0  # skipped

    def test_get_list_shape_limit_and_next_before_id(self, api_client):
        resp = api_client.get("/object?limit=1")
        assert resp.status_code == 200
        payload = resp.json()
        _assert_list_shape(payload)

        assert len(payload["items"]) <= 1
        if payload["items"]:
            _assert_object_row_shape(payload["items"][0])
            assert payload["next_before_id"] == payload["items"][-1]["id"]

    def test_get_before_id_excludes_boundary(self, api_client, object_registry):
        # Ensure we have at least 2 objects to paginate through
        o1 = _create_one(api_client, name=f"{_rand('page')}.txt", content=b"x")
        _register_created(object_registry, o1.get("objects_created", []))
        o2 = _create_one(api_client, name=f"{_rand('page')}.txt", content=b"y")
        _register_created(object_registry, o2.get("objects_created", []))

        r1 = api_client.get("/object?limit=1")
        assert r1.status_code == 200
        p1 = r1.json()
        _assert_list_shape(p1)
        assert len(p1["items"]) == 1
        before_id = p1["next_before_id"]
        assert before_id is not None

        r2 = api_client.get(f"/object?limit=50&before_id={before_id}")
        assert r2.status_code == 200
        p2 = r2.json()
        _assert_list_shape(p2)

        # strict id < before_id
        assert all(item["id"] < before_id for item in p2["items"])

    def test_get_slug_filters_by_prefix(self, api_client, object_registry):
        slug = _rand("folder")
        k1 = f"{slug}/a.txt"
        k2 = f"{slug}/b.txt"
        other = f"{_rand('other')}/c.txt"

        r1 = _post_object_files(api_client, [("object", (k1, b"a", "text/plain"))])
        r2 = _post_object_files(api_client, [("object", (k2, b"b", "text/plain"))])
        r3 = _post_object_files(api_client, [("object", (other, b"c", "text/plain"))])
        assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200

        _register_created(object_registry, r1.json()["objects_created"])
        _register_created(object_registry, r2.json()["objects_created"])
        _register_created(object_registry, r3.json()["objects_created"])

        resp = api_client.get(f"/object?slug={slug}&limit=200")
        assert resp.status_code == 200
        payload = resp.json()
        _assert_list_shape(payload)

        keys = [it["key"] for it in payload["items"]]
        assert keys  # should find at least those we inserted
        assert all(k.startswith(f"{slug}/") for k in keys)

    def test_get_single_404(self, api_client):
        resp = api_client.get("/object/999999999")
        assert resp.status_code == 404

    def test_patch_updates_source_and_mime_type(self, api_client, object_registry):
        created = _create_one(api_client, name=f"{_rand('patch')}.txt", content=b"z")
        objs = created["objects_created"]
        assert len(objs) == 1
        _register_created(object_registry, objs)
        oid = objs[0]["id"]

        resp = api_client.patch(f"/object/{oid}", json={"source": {"comments": "test"}})
        assert resp.status_code == 200
        out = resp.json()
        _assert_object_row_shape(out)
        assert isinstance(out["source"], dict)
        assert out["source"]["comments"] == "test"

        resp2 = api_client.patch(f"/object/{oid}", json={"mime_type": "application/pdf"})
        assert resp2.status_code == 200
        assert resp2.json()["mime_type"] == "application/pdf"

    def test_patch_404(self, api_client):
        resp = api_client.patch("/object/999999999", json={"source": {"x": 1}})
        assert resp.status_code == 404

    def test_soft_delete_and_include_deleted(self, api_client, object_registry):
        created = _create_one(api_client, name=f"{_rand('soft')}.txt", content=b"s")
        objs = created["objects_created"]
        assert len(objs) == 1
        _register_created(object_registry, objs)
        oid = objs[0]["id"]

        # soft delete
        r = api_client.delete(f"/object/{oid}?hard=false")
        assert r.status_code == 200
        payload = r.json()
        assert payload["status"] == "deleted"
        assert payload["hard"] is False
        assert payload["object"]["id"] == oid
        assert payload["object"]["deleted_on"] is not None

        # list without include_deleted should not include it
        r2 = api_client.get("/object?limit=500")
        assert r2.status_code == 200
        ids = [it["id"] for it in r2.json()["items"]]
        assert oid not in ids

        # list with include_deleted should include it
        r3 = api_client.get("/object?include_deleted=true&limit=500")
        assert r3.status_code == 200
        ids3 = [it["id"] for it in r3.json()["items"]]
        assert oid in ids3

        # IMPORTANT: soft deleted objects are still in registry and will be hard-deleted at teardown.

    def test_delete_404(self, api_client):
        resp = api_client.delete("/object/999999999?hard=true")
        assert resp.status_code == 404

    def test_unimplemented_routes_501(self, api_client):
        r1 = api_client.post("/object/1/track")
        assert r1.status_code == 501
        r2 = api_client.post("/object/1/forget")
        assert r2.status_code == 501
        r3 = api_client.get("/object/1/url")
        assert r3.status_code == 501
