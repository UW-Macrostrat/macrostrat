# /Users/afromandi/Macrostrat/Projects/macrostrat/services/api-v3/api/tests/test_convert_field_site.py

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from .test_database import api_client


def test__debug_routes(api_client):
    paths = sorted({r.path for r in api_client.app.router.routes if hasattr(r, "path")})
    print("\n".join(paths))
    assert True


def _spot_feature(
    *,
    spot_id: int = 123,
    lat: float = 43.0,
    lng: float = -89.0,
    orientations: List[Dict[str, Any]] | None = None,
    include_images: bool = True,
    image_basemap: Any = None,
    geom_type: str = "Point",
) -> Dict[str, Any]:
    """
    Build a StraboSpot GeoJSON Feature.

    orientations: list of {"strike": float, "dip": float} dicts.
                  Pass [] or omit to produce no orientation_data.
                  Defaults to a single planar orientation for convenience.
    """
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

    # Default: one planar orientation
    if orientations is None:
        orientations = [{"strike": 123.0, "dip": 45.0}]

    if orientations:
        props["orientation_data"] = [
            {"type": "planar_orientation", "strike": o["strike"], "dip": o["dip"]}
            for o in orientations
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
    orientations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Build a Rockd checkin dict.

    orientations: list of {"strike": float, "dip": float} dicts.
                  Pass [] to produce no observations with orientation.
                  Defaults to a single observation for convenience.
    """
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

    # Default: one observation with orientation
    if orientations is None:
        orientations = [{"strike": 10.0, "dip": 20.0}]

    d["observations"] = [
        {"orientation": {"strike": o["strike"], "dip": o["dip"]}}
        for o in orientations
    ]
    return d


def _fieldsite_dict(
    *,
    fs_id: int = 88,
    lat: float = 43.0,
    lng: float = -89.0,
    include_photo: bool = True,
    orientations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Build a FieldSite dict.

    orientations: list of {"strike": float, "dip": float} dicts.
                  Pass [] to produce no observations.
                  Defaults to a single planar observation for convenience.
    """
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
            {
                "id": 321,
                "url": "rockd://photo/321",
                "width": 0,
                "height": 0,
                "checksum": "",
            }
        ]

    # Default: one planar observation
    if orientations is None:
        orientations = [{"strike": 111.0, "dip": 33.0}]

    d["observations"] = [
        {"data": {"strike": o["strike"], "dip": o["dip"], "facing": "upright"}}
        for o in orientations
    ]
    return d


class TestConvertFieldSite:
    # ─────────────────────────── spot → fieldsite ────────────────────────────

    def test_spot_to_fieldsite_featurecollection(self, api_client):
        payload = _spot_featurecollection(
            [
                _spot_feature(spot_id=1),
                _spot_feature(spot_id=2, orientations=[]),
            ]
        )

        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=fieldsite", json=payload
        )
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

        # first spot has one planar, second has none
        assert len(data[0]["observations"]) == 1
        assert len(data[1]["observations"]) == 0

    def test_spot_to_fieldsite_multiple_orientations(self, api_client):
        """All planar orientations in a spot are preserved — not just the first."""
        payload = _spot_featurecollection([
            _spot_feature(
                spot_id=1,
                orientations=[
                    {"strike": 10.0, "dip": 5.0},
                    {"strike": 90.0, "dip": 45.0},
                    {"strike": 180.0, "dip": 30.0},
                ],
            )
        ])

        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        obs = data[0]["observations"]
        assert len(obs) == 3
        strikes = [o["data"]["strike"] for o in obs]
        assert strikes == pytest.approx([10.0, 90.0, 180.0])
        dips = [o["data"]["dip"] for o in obs]
        assert dips == pytest.approx([5.0, 45.0, 30.0])

    def test_spot_to_fieldsite_filters_non_point_and_image_basemap(self, api_client):
        payload = _spot_featurecollection(
            [
                _spot_feature(spot_id=1, geom_type="LineString"),
                _spot_feature(spot_id=2, image_basemap="something"),  # skipped
                _spot_feature(spot_id=3),                              # survives
            ]
        )

        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 3

    def test_spot_to_fieldsite_invalid_coords_skips_feature(self, api_client):
        payload = _spot_featurecollection(
            [_spot_feature(spot_id=1, lat=999.0, lng=-89.0)]
        )
        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        assert resp.json() == []

    # ─────────────────────────── spot → checkin ──────────────────────────────

    def test_spot_to_checkin_from_featurecollection(self, api_client):
        payload = _spot_featurecollection([_spot_feature(spot_id=10)])
        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=checkin", json=payload
        )
        assert resp.status_code == 200

        c = resp.json()
        assert isinstance(c, dict)
        assert c["checkin_id"] == 10
        assert c["spot_id"] == 10
        assert c["lat"] == pytest.approx(43.0)
        assert c["lng"] == pytest.approx(-89.0)
        assert c["created"].endswith("Z")
        assert c["updated"].endswith("Z")

        assert "observations" in c and isinstance(c["observations"], list)
        assert len(c["observations"]) == 1
        assert c["observations"][0]["orientation"]["strike"] == pytest.approx(123.0)
        assert c["observations"][0]["orientation"]["dip"] == pytest.approx(45.0)

    def test_spot_to_checkin_multiple_orientations(self, api_client):
        """All planar orientations flow through the spot → checkin pipeline."""
        payload = _spot_featurecollection([
            _spot_feature(
                spot_id=10,
                orientations=[
                    {"strike": 10.0, "dip": 5.0},
                    {"strike": 90.0, "dip": 45.0},
                ],
            )
        ])
        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=checkin", json=payload
        )
        assert resp.status_code == 200
        c = resp.json()
        assert len(c["observations"]) == 2
        assert c["observations"][0]["orientation"]["strike"] == pytest.approx(10.0)
        assert c["observations"][1]["orientation"]["strike"] == pytest.approx(90.0)

    def test_spot_to_checkin_no_orientation_produces_empty_observations(self, api_client):
        payload = _spot_featurecollection([_spot_feature(spot_id=10, orientations=[])])
        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=checkin", json=payload
        )
        assert resp.status_code == 200
        c = resp.json()
        assert "observations" in c
        assert c["observations"] == []

    def test_spot_to_checkin_accepts_single_fieldsite_dict(self, api_client):
        payload = _fieldsite_dict(fs_id=501)
        resp = api_client.post(
            "/dev/convert/field-site?in=spot&out=checkin", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        assert isinstance(out, dict)
        assert out["checkin_id"] == 501
        assert out["spot_id"] == 501
        assert out["created"].endswith("Z")
        assert out["updated"].endswith("Z")

    # ─────────────────────────── checkin → fieldsite ─────────────────────────

    def test_checkin_to_fieldsite_single(self, api_client):
        payload = _checkin(checkin_id=77)
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200

        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 1

        fs = out[0]
        assert fs["id"] == 77
        assert fs["location"]["latitude"] == pytest.approx(43.0)
        assert fs["location"]["longitude"] == pytest.approx(-89.0)
        assert len(fs["observations"]) == 1
        assert fs["observations"][0]["data"]["strike"] == pytest.approx(10.0)
        assert fs["observations"][0]["data"]["dip"] == pytest.approx(20.0)

    def test_checkin_to_fieldsite_multiple_orientations(self, api_client):
        """All observations with valid strike/dip are preserved."""
        payload = _checkin(
            checkin_id=77,
            orientations=[
                {"strike": 123.0, "dip": 35.0},
                {"strike": 45.0,  "dip": 10.0},
            ],
        )
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        fs = resp.json()[0]
        assert len(fs["observations"]) == 2
        assert fs["observations"][0]["data"]["strike"] == pytest.approx(123.0)
        assert fs["observations"][1]["data"]["strike"] == pytest.approx(45.0)

    def test_checkin_to_fieldsite_empty_orientation_skipped(self, api_client):
        """Observations with empty/null orientation dict are silently dropped."""
        payload = {
            "checkin_id": 77,
            "lat": 43.0,
            "lng": -89.0,
            "observations": [
                {"orientation": {"strike": 123.0, "dip": 35.0}},
                {"orientation": {}},          # no strike/dip — skipped
                {"orientation": None},         # null — skipped
            ],
        }
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        fs = resp.json()[0]
        assert len(fs["observations"]) == 1
        assert fs["observations"][0]["data"]["strike"] == pytest.approx(123.0)

    def test_checkin_to_fieldsite_no_orientation(self, api_client):
        payload = _checkin(checkin_id=77, orientations=[])
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        fs = resp.json()[0]
        assert fs["observations"] == []

    def test_checkin_to_fieldsite_list(self, api_client):
        payload = [
            _checkin(checkin_id=1),
            _checkin(checkin_id=2, orientations=[]),
        ]
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 2
        assert {o["id"] for o in out} == {1, 2}
        # first has observation, second does not
        fs1 = next(o for o in out if o["id"] == 1)
        fs2 = next(o for o in out if o["id"] == 2)
        assert len(fs1["observations"]) == 1
        assert len(fs2["observations"]) == 0

    # ─────────────────────────── fieldsite → checkin ─────────────────────────

    def test_fieldsite_to_checkin_list(self, api_client):
        payload = [
            _fieldsite_dict(fs_id=900),
            _fieldsite_dict(fs_id=901, orientations=[]),
        ]
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=checkin", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        assert isinstance(out, list)
        assert len(out) == 2

        c0 = next(c for c in out if c["checkin_id"] == 900)
        c1 = next(c for c in out if c["checkin_id"] == 901)

        assert c0["spot_id"] == 900
        assert c0["created"].endswith("Z")
        assert c0["updated"].endswith("Z")
        assert len(c0["observations"]) == 1
        assert c0["observations"][0]["orientation"]["strike"] == pytest.approx(111.0)
        assert c0["observations"][0]["orientation"]["dip"] == pytest.approx(33.0)

        # no orientations → empty observations list still present
        assert "observations" in c1
        assert c1["observations"] == []

    def test_fieldsite_to_checkin_multiple_orientations(self, api_client):
        """All planar observations are emitted into the checkin observations list."""
        payload = _fieldsite_dict(
            fs_id=900,
            orientations=[
                {"strike": 10.0, "dip": 5.0},
                {"strike": 90.0, "dip": 45.0},
                {"strike": 180.0, "dip": 30.0},
            ],
        )
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=checkin", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        # single fieldsite payload returns a single dict
        assert isinstance(out, dict)
        assert len(out["observations"]) == 3
        strikes = [o["orientation"]["strike"] for o in out["observations"]]
        assert strikes == pytest.approx([10.0, 90.0, 180.0])

    def test_fieldsite_to_checkin_single_returns_dict(self, api_client):
        payload = _fieldsite_dict(fs_id=999)
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=checkin", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        assert isinstance(out, dict)
        assert out["checkin_id"] == 999
        assert out["spot_id"] == 999
        assert out["created"].endswith("Z")
        assert out["updated"].endswith("Z")
        assert "observations" in out

    # ─────────────────────────── fieldsite → spot ────────────────────────────

    def test_fieldsite_to_spot_single(self, api_client):
        payload = _fieldsite_dict(fs_id=1234)
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=spot", json=payload
        )
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        f0 = fc["features"][0]
        assert f0["type"] == "Feature"
        assert f0["geometry"]["type"] == "Point"
        assert f0["properties"]["id"] == 1234

        od = f0["properties"]["orientation_data"]
        assert isinstance(od, list)
        assert len(od) == 1
        assert od[0]["type"] == "planar_orientation"
        assert od[0]["strike"] == pytest.approx(111.0)
        assert od[0]["dip"] == pytest.approx(33.0)

    def test_fieldsite_to_spot_multiple_orientations(self, api_client):
        """All planar observations are written into orientation_data."""
        payload = _fieldsite_dict(
            fs_id=1234,
            orientations=[
                {"strike": 10.0, "dip": 5.0},
                {"strike": 90.0, "dip": 45.0},
            ],
        )
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=spot", json=payload
        )
        assert resp.status_code == 200
        fc = resp.json()
        od = fc["features"][0]["properties"]["orientation_data"]
        assert len(od) == 2
        assert od[0]["strike"] == pytest.approx(10.0)
        assert od[1]["strike"] == pytest.approx(90.0)

    def test_fieldsite_to_spot_no_orientation_omits_key(self, api_client):
        """When there are no orientations, orientation_data is omitted entirely."""
        payload = _fieldsite_dict(fs_id=1234, orientations=[])
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=spot", json=payload
        )
        assert resp.status_code == 200
        props = resp.json()["features"][0]["properties"]
        assert "orientation_data" not in props

    def test_fieldsite_to_spot_list(self, api_client):
        payload = [_fieldsite_dict(fs_id=1), _fieldsite_dict(fs_id=2)]
        resp = api_client.post(
            "/dev/convert/field-site?in=fieldsite&out=spot", json=payload
        )
        assert resp.status_code == 200
        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        ids = {f["properties"]["id"] for f in fc["features"]}
        assert ids == {1, 2}

    # ─────────────────────────── checkin → spot ──────────────────────────────

    def test_checkin_to_spot_single(self, api_client):
        payload = _checkin(checkin_id=321)
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=spot", json=payload
        )
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 1
        assert fc["features"][0]["properties"]["id"] == 321

        od = fc["features"][0]["properties"]["orientation_data"]
        assert len(od) == 1
        assert od[0]["strike"] == pytest.approx(10.0)
        assert od[0]["dip"] == pytest.approx(20.0)

    def test_checkin_to_spot_multiple_orientations(self, api_client):
        """All observations with valid orientation flow through to spot orientation_data."""
        payload = _checkin(
            checkin_id=321,
            orientations=[
                {"strike": 10.0, "dip": 5.0},
                {"strike": 90.0, "dip": 45.0},
            ],
        )
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=spot", json=payload
        )
        assert resp.status_code == 200
        od = resp.json()["features"][0]["properties"]["orientation_data"]
        assert len(od) == 2
        assert od[0]["strike"] == pytest.approx(10.0)
        assert od[1]["strike"] == pytest.approx(90.0)

    def test_checkin_to_spot_list(self, api_client):
        payload = [_checkin(checkin_id=1), _checkin(checkin_id=2)]
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=spot", json=payload
        )
        assert resp.status_code == 200

        fc = resp.json()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        ids = {f["properties"]["id"] for f in fc["features"]}
        assert ids == {1, 2}

    # ─────────────────────────── real fixture ────────────────────────────────

    def test_checkin_to_fieldsite_real_fixture(self, api_client):
        """
        checkin-26692 has 3 observations; only obs 44348 has a valid
        strike (123) / dip (35). The other two have empty orientation dicts.
        After conversion exactly one PlanarOrientation should survive.
        """
        import json, pathlib
        fixture_path = pathlib.Path(__file__).parent / "fixtures" / "checkin-26692.json"
        if not fixture_path.exists():
            pytest.skip("checkin-26692.json fixture not found")

        payload = json.loads(fixture_path.read_text())
        resp = api_client.post(
            "/dev/convert/field-site?in=checkin&out=fieldsite", json=payload
        )
        assert resp.status_code == 200
        out = resp.json()
        assert len(out) == 1
        fs = out[0]
        assert fs["id"] == 26692
        assert len(fs["observations"]) == 1
        assert fs["observations"][0]["data"]["strike"] == pytest.approx(123.0)
        assert fs["observations"][0]["data"]["dip"] == pytest.approx(35.0)

    # ─────────────────────────── error handling ──────────────────────────────

    def test_unsupported_conversion_400(self, api_client):
        resp = api_client.post(
            "/dev/convert/field-site?in=banana&out=fieldsite", json={}
        )
        assert resp.status_code == 400
        detail = resp.json().get("detail")
        assert isinstance(detail, str)