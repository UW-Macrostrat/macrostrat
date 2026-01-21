# /Users/afromandi/Macrostrat/Projects/macrostrat/services/api-v3/api/tests/test_convert_field_site.py

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from .test_database import api_client


def test__debug_routes(api_client):
    paths = sorted(
        {r.path for r in api_client.app.router.routes if hasattr(r, "path")}
    )
    print("\n".join(paths))
    assert True



def _spot_feature(
    *,
    spot_id: int = 123,
    lat: float = 43.0,
    lng: float = -89.0,
    include_orientation: bool = True,
    include_images: bool = True,
    image_basemap: Any = None,
    geom_type: str = "Point",
) -> Dict[str, Any]:
    props: Dict[str, Any] = {
        "id": spot_id,
        "lat": lat,
        "lng": lng,
        "notes": "hello",
        "time": "2023-10-19T12:00:00Z",
        "modified_timestamp": 1697716800000,
    }
    if image_basemap is not None:
        props["image_basemap"] = image_basemap

    if include_images:
        props["images"] = [{"id": 777, "width": 100, "height": 200}]

    if include_orientation:
        props["orientation_data"] = [
            {"type": "planar_orientation", "strike": 123.0, "dip": 45.0}
        ]

    geom: Dict[str, Any] = (
        {"type": "Point", "coordinates": [lng, lat]}
        if geom_type == "Point"
        else {"type": geom_type, "coordinates": []}
    )

    return {"type": "Feature", "properties": props, "geometry": geom}


def _spot_featurecollection(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def _checkin(
    *,
    checkin_id: int = 55,
    lat: float = 43.0,
    lng: float = -89.0,
    include_photo: bool = True,
    include_orientation: bool = True,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "checkin_id": checkin_id,
        "lat": lat,
        "lng": lng,
        "notes": "note",
        "created": "October 19, 2023",
        "added": "October 20, 2023",
    }
    if include_photo:
        d["photo"] = 999
    if include_orientation:
        d["observations"] = [{"orientation": {"strike": 10.0, "dip": 20.0}}]
    else:
        d["observations"] = []
    return d


def _fieldsite_dict(
    *,
    fs_id: int = 88,
    lat: float = 43.0,
    lng: float = -89.0,
    include_photo: bool = True,
    include_orientation: bool = True,
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": fs_id,
        "notes": "fs note",
        "created": "2023-10-19T12:00:00+00:00",
        "updated": "2023-10-20T12:00:00+00:00",
        "location": {"latitude": lat, "longitude": lng},
        "photos": [],
        "observations": [],
    }

    if include_photo:
        d["photos"] = [
            {"id": 321, "url": "rockd://photo/321", "width": 0, "height": 0, "checksum": ""}
        ]

    if include_orientation:
        d["observations"] = [
            {"data": {"strike": 111.0, "dip": 33.0, "facing": "upright"}}
        ]

    return d


class TestConvertFieldSite:
    def test_spot_to_fieldsite_featurecollection(self, api_client):
        payload = _spot_featurecollection(
            [
                _spot_feature(spot_id=1),
                _spot_feature(spot_id=2, include_orientation=False),
            ]
        )

        resp = api_client.post("/dev/convert/field-site?in=spot&out=fieldsite", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

        # basic FieldSite shape
        assert data[0]["id"] == 1
        assert "location" in data[0]
        assert "latitude" in data[0]["location"]
        assert "longitude" in data[0]["location"]
        assert data[0]["location"]["latitude"] == pytest.approx(43.0)
        assert data[0]["location"]["longitude"] == pytest.approx(-89.0)

        # observations for first has planar, second does not
        assert isinstance(data[0].get("observations"), list)
        assert isinstance(data[1].get("observations"), list)

    def test_spot_to_fieldsite_filters_non_point_and_image_basemap(self, api_client):
        payload = _spot_featurecollection(
            [
                _spot_feature(spot_id=1, geom_type="LineString"),
                _spot_feature(spot_id=2, image_basemap="something"),  # should be skipped
                _spot_feature(spot_id=3),  # should survive
            ]
        )

        resp = api_client.post("/dev/convert/field-site?in=spot&out=fieldsite", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 3

    def test_spot_to_fieldsite_invalid_coords_skips_feature(self, api_client):
        payload = _spot_featurecollection([_spot_feature(spot_id=1, lat=999.0, lng=-89.0)])
        resp = api_client.post("/dev/convert/field-site?in=spot&out=fieldsite", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data == []  # invalid spot should be skipped

    def test_spot_to_checkin_from_featurecollection(self, api_client):
        payload = _spot_featurecollection([_spot_feature(spot_id=10)])
        resp = api_client.post("/dev/convert/field-site?in=spot&out=checkin", json=payload)
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 1

        c = out[0]
        # Rockd checkin-ish keys
        assert c["checkin_id"] == 10
        assert c["spot_id"] == 10
        assert c["lat"] == pytest.approx(43.0)
        assert c["lng"] == pytest.approx(-89.0)
        assert "created" in c and isinstance(c["created"], str)
        assert "added" in c and isinstance(c["added"], str)
        assert "observations" in c and isinstance(c["observations"], list)

        # orientation passed through
        assert len(c["observations"]) == 1
        assert "orientation" in c["observations"][0]
        assert c["observations"][0]["orientation"]["strike"] == pytest.approx(123.0)
        assert c["observations"][0]["orientation"]["dip"] == pytest.approx(45.0)

    def test_spot_to_checkin_accepts_single_fieldsite_dict(self, api_client):
        # your spot_to_checkin treats dict with "location" as already-FieldSite-shaped
        payload = _fieldsite_dict(fs_id=501)
        resp = api_client.post("/dev/convert/field-site?in=spot&out=checkin", json=payload)
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["checkin_id"] == 501
        assert out[0]["spot_id"] == 501

    def test_checkin_to_fieldsite_single(self, api_client):
        payload = _checkin(checkin_id=77)
        resp = api_client.post("/dev/convert/field-site?in=checkin&out=fieldsite", json=payload)
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 1

        fs = out[0]
        assert fs["id"] == 77
        assert fs["location"]["latitude"] == pytest.approx(43.0)
        assert fs["location"]["longitude"] == pytest.approx(-89.0)
        assert "observations" in fs and isinstance(fs["observations"], list)

    def test_checkin_to_fieldsite_list(self, api_client):
        payload = [_checkin(checkin_id=1), _checkin(checkin_id=2, include_orientation=False)]
        resp = api_client.post("/dev/convert/field-site?in=checkin&out=fieldsite", json=payload)
        assert resp.status_code == 200
        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 2
        assert {o["id"] for o in out} == {1, 2}

    def test_fieldsite_to_checkin_list(self, api_client):
        payload = [_fieldsite_dict(fs_id=900), _fieldsite_dict(fs_id=901, include_orientation=False)]
        resp = api_client.post("/dev/convert/field-site?in=fieldsite&out=checkin", json=payload)
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 2

        c0 = out[0]
        assert c0["checkin_id"] == 900
        assert c0["spot_id"] == 900
        assert "created" in c0 and isinstance(c0["created"], str)
        assert "added" in c0 and isinstance(c0["added"], str)

    def test_fieldsite_to_checkin_single_returns_list_of_one(self, api_client):
        payload = _fieldsite_dict(fs_id=999)
        resp = api_client.post("/dev/convert/field-site?in=fieldsite&out=checkin", json=payload)
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["checkin_id"] == 999
        assert out[0]["spot_id"] == 999

    def test_fieldsite_to_spot_single(self, api_client):
        payload = _fieldsite_dict(fs_id=1234)
        resp = api_client.post("/dev/convert/field-site?in=fieldsite&out=spot", json=payload)
        assert resp.status_code == 200

        fc = resp.json()
        assert isinstance(fc, dict)
        assert fc["type"] == "FeatureCollection"
        assert isinstance(fc.get("features"), list)
        assert len(fc["features"]) == 1
        f0 = fc["features"][0]
        assert f0["type"] == "Feature"
        assert f0["geometry"]["type"] == "Point"
        assert f0["properties"]["id"] == 1234

    def test_fieldsite_to_spot_list(self, api_client):
        payload = [_fieldsite_dict(fs_id=1), _fieldsite_dict(fs_id=2)]
        resp = api_client.post("/dev/convert/field-site?in=fieldsite&out=spot", json=payload)
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        ids = {f["properties"]["id"] for f in fc["features"]}
        assert ids == {1, 2}

    def test_checkin_to_spot_single(self, api_client):
        payload = _checkin(checkin_id=321)
        resp = api_client.post("/dev/convert/field-site?in=checkin&out=spot", json=payload)
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        assert fc["features"][0]["properties"]["id"] == 321

    def test_checkin_to_spot_list(self, api_client):
        payload = [_checkin(checkin_id=1), _checkin(checkin_id=2)]
        resp = api_client.post("/dev/convert/field-site?in=checkin&out=spot", json=payload)
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        ids = {f["properties"]["id"] for f in fc["features"]}
        assert ids == {1, 2}

    def test_unsupported_conversion_400(self, api_client):
        resp = api_client.post("/dev/convert/field-site?in=banana&out=fieldsite", json={})
        assert resp.status_code == 400
        detail = resp.json().get("detail")
        assert isinstance(detail, str)
