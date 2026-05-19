from typing import Any, Iterable, List, Optional, Union
from datetime import datetime, timezone

import dotenv
dotenv.load_dotenv()

from fastapi import HTTPException
from api.routes.dev_routes.field_site import (
    BeddingFacing, FieldSite, Location, Observation, Photo, PlanarOrientation,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _dt_to_ms(dt: Optional[datetime]) -> Optional[int]:
    return int(_ensure_utc(dt).timestamp() * 1000) if dt else None

def _dt_to_iso_z(dt: Optional[datetime]) -> Optional[str]:
    return _ensure_utc(dt).astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if dt else None

def _to_float(v) -> Optional[float]:
    try: return None if v is None else float(v)
    except Exception: return None

def _valid_coords(lat, lng) -> bool:
    lat, lng = _to_float(lat), _to_float(lng)
    return lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180

def _parse_date_time(x: Optional[str]) -> Optional[datetime]:
    if not x:
        return None
    for parser in (
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
        lambda s: datetime.strptime(s, "%B %d, %Y").replace(tzinfo=timezone.utc),
    ):
        try: return parser(x)
        except Exception: pass
    return None

def _iter_spot_features(payload: Any) -> Iterable[dict]:
    for item in (payload if isinstance(payload, list) else [payload]):
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if t == "Feature":
            yield item
        elif t == "FeatureCollection" or "features" in item:
            yield from (
                f for f in (item.get("features") or [])
                if isinstance(f, dict) and f.get("type") == "Feature"
            )

def _planars(items: list, strike_key: str, dip_key: str) -> list[PlanarOrientation]:
    out = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        s, d = _to_float(item.get(strike_key)), _to_float(item.get(dip_key))
        if s is not None and d is not None:
            out.append(PlanarOrientation(strike=s, dip=d, facing=BeddingFacing.upright))
    return out

def _all_planars_from_spot(props) -> list[PlanarOrientation]:
    return _planars(
        [i for i in (props.get("orientation_data") or [])
         if isinstance(i, dict) and i.get("type") == "planar_orientation"],
        "strike", "dip",
    )

def _all_planars_from_checkin(checkin) -> list[PlanarOrientation]:
    return _planars(
        [o.get("orientation") or {} for o in (checkin.get("observations") or [])
         if isinstance(o, dict)],
        "strike", "dip",
    )

def _all_planars_from_fieldsite(fs: FieldSite) -> list[PlanarOrientation]:
    return [
        ob.data for ob in (fs.observations or [])
        if isinstance(getattr(ob, "data", None), PlanarOrientation)
    ]


# ── Spot → FieldSite ──────────────────────────────────────────────────────────

def spot_to_fieldsite(feat: dict) -> FieldSite:
    props = feat.get("properties") or {}
    geom = feat.get("geometry") or {}
    sid = props.get("id")
    if sid is None:
        raise ValueError("Missing spot properties.id")
    lat, lng = props.get("lat"), props.get("lng")
    if (lat is None or lng is None) and geom.get("type") == "Point":
        coords = geom.get("coordinates") or []
        if len(coords) >= 2:
            lng = coords[0] if lng is None else lng
            lat = coords[1] if lat is None else lat
    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Spot feature")
    photos = []
    images = props.get("images") or []
    if images and (img := images[0] or {}) and img.get("id") is not None:
        photos.append(Photo(
            id=int(img["id"]), url="https://dev.rockd.org/api/v2/protected/photos",
            width=int(img.get("width") or 0), height=int(img.get("height") or 0), checksum="",
        ))
    created = _parse_date_time(props.get("time") or props.get("date")) or datetime.now(timezone.utc)
    mt = props.get("modified_timestamp")
    updated = datetime.fromtimestamp(float(mt) / 1000, tz=timezone.utc) if mt is not None else created
    return FieldSite(
        id=sid, location=Location(latitude=float(lat), longitude=float(lng)),
        created=created, updated=updated, notes=props.get("name") or props.get("notes"),
        photos=photos, observations=[Observation(data=p) for p in _all_planars_from_spot(props)],
    )

def multiple_spot_to_fieldsite(payload: Union[dict, List[dict]]) -> List[FieldSite]:
    out = []
    for feat in _iter_spot_features(payload):
        props, geom = feat.get("properties") or {}, feat.get("geometry") or {}
        if geom.get("type") != "Point" or props.get("image_basemap") is not None or props.get("id") is None:
            continue
        try: out.append(spot_to_fieldsite(feat))
        except Exception: pass
    return out


# ── Checkin → FieldSite ───────────────────────────────────────────────────────

def checkin_to_fieldsite(checkin: dict) -> FieldSite:
    if not isinstance(checkin, dict):
        raise ValueError("Checkin must be a dict")
    cid = checkin.get("checkin_id")
    if cid is None:
        raise ValueError("Missing checkin_id")
    lat, lng = checkin.get("lat"), checkin.get("lng")
    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Checkin")
    photos = []
    pid = checkin.get("photo")
    if isinstance(pid, int):
        photos.append(Photo(id=pid, url=f"rockd://photo/{pid}", width=0, height=0, checksum=""))
    created = _parse_date_time(checkin.get("created")) or datetime.now(timezone.utc)
    updated = _parse_date_time(checkin.get("updated")) or _parse_date_time(checkin.get("added")) or created
    return FieldSite(
        id=int(cid), location=Location(latitude=float(lat), longitude=float(lng)),
        created=created, updated=updated, notes=checkin.get("notes"),
        photos=photos, observations=[Observation(data=p) for p in _all_planars_from_checkin(checkin)],
    )

def multiple_checkin_to_fieldsite(payload: Union[dict, List[dict]]) -> List[FieldSite]:
    out = []
    for c in (payload if isinstance(payload, list) else [payload]):
        if isinstance(c, dict):
            try: out.append(checkin_to_fieldsite(c))
            except Exception: pass
    return out


# ── FieldSite → Checkin ───────────────────────────────────────────────────────

def fieldsite_to_rockd_checkin(fs: FieldSite) -> dict:
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)
    created = fs.created or datetime.now(timezone.utc)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    d = {
        "notes": (fs.notes or "").strip(), "rating": 0,
        "lat": float(fs.location.latitude), "lng": float(fs.location.longitude),
        "created": _dt_to_iso_z(created),
        "spot_id": int(fs.id) if fs.id is not None else None,
        "new_checkin_id": str(now_ms),
    }
    if fs.photos:
        d["photo"] = f"{int(fs.photos[0].id)}.jpg"
    d["observations"] = [
        {
            "new_obs_id": f"interchange_obs_{i}_{now_ms}",
            "rocks": {"strat_name": {}, "liths": [], "interval": {}, "notes": "", "map_unit": {}},
            "minerals": {"minerals": [], "notes": ""},
            "orientation": {
                "strike": _to_float(p.strike), "strikestd": None,
                "dip": _to_float(p.dip), "dipstd": None,
                "dip_dir": None, "feature": {}, "notes": "",
                "trend": None, "trendstd": None, "plunge": None, "plungestd": None,
            },
            "fossils": {"taxa": [], "notes": ""},
        }
        for i, p in enumerate(_all_planars_from_fieldsite(fs))
    ]
    return d

def multiple_fieldsite_to_rockd_checkin(fieldsites: Union[list[FieldSite], list[dict]]) -> list[dict]:
    out = []
    for fs in fieldsites or []:
        try:
            if not isinstance(fs, FieldSite): fs = FieldSite(**fs)
            out.append(fieldsite_to_rockd_checkin(fs))
        except Exception: pass
    return out


# ── FieldSite → Spot ──────────────────────────────────────────────────────────

def _fieldsite_to_spot_feature(fs: FieldSite) -> dict:
    """Build a StraboSpot GeoJSON Feature from a FieldSite (FeatureCollection format)."""
    if not isinstance(fs, FieldSite): fs = FieldSite(**fs)
    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created
    feat = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [fs.location.longitude, fs.location.latitude]},
        "properties": {
            "id": fs.id, "notes": fs.notes,
            "time": _dt_to_iso_z(created), "date": _dt_to_iso_z(created),
            "modified_timestamp": _dt_to_ms(updated),
            "lat": fs.location.latitude, "lng": fs.location.longitude,
        },
    }
    if fs.photos:
        feat["properties"]["images"] = [
            {"id": int(p.id), "width": int(getattr(p, "width", 0) or 0),
             "height": int(getattr(p, "height", 0) or 0), "title": "", "image_type": "photo"}
            for p in fs.photos
        ]
    planars = _all_planars_from_fieldsite(fs)
    if planars:
        feat["properties"]["orientation_data"] = [
            {"type": "planar_orientation", "strike": float(p.strike), "dip": float(p.dip)}
            for p in planars
        ]
    return feat

def _fieldsite_to_spot_single(fs: FieldSite) -> dict:
    """Build a bare StraboSpot Feature from a FieldSite (single-object format)."""
    if not isinstance(fs, FieldSite): fs = FieldSite(**fs)
    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created
    feat = {
        "type": "Feature",
        "properties": {
            "images": [], "time": _dt_to_iso_z(created), "id": fs.id,
            "orientation_data": [], "modified_timestamp": _dt_to_ms(updated),
            "date": _dt_to_iso_z(created), "samples": [], "name": fs.notes or "",
        },
        "geometry": {"type": "Point", "coordinates": [fs.location.longitude, fs.location.latitude]},
    }
    if fs.photos:
        feat["properties"]["images"] = [
            {"height": int(getattr(p, "height", 0) or 0), "id": int(p.id),
             "annotated": False, "title": "", "width": int(getattr(p, "width", 0) or 0), "caption": ""}
            for p in fs.photos
        ]
    planars = _all_planars_from_fieldsite(fs)
    if planars:
        feat["properties"]["orientation_data"] = [
            {
                "dip_direction": None, "strike": _to_float(p.strike), "dip": _to_float(p.dip),
                "facing": p.facing.value if getattr(p, "facing", None) is not None else "upright",
                "orientation_type": "planar_orientation",
            }
            for p in planars
        ]
    return feat

def fieldsite_to_spot(payload: Union[FieldSite, dict, List], bulk: bool = False) -> dict:
    """
    bulk=True  → accept a list of FieldSites, return a FeatureCollection with all features.
    bulk=False → accept a single FieldSite, return a FeatureCollection with one feature.
    """
    if bulk:
        features = []
        for fs in payload or []:
            try: features.append(_fieldsite_to_spot_feature(fs))
            except Exception: pass
        return {"type": "FeatureCollection", "features": features}
    return {"type": "FeatureCollection", "features": [_fieldsite_to_spot_feature(payload)]}


# ── Checkin ↔ Spot ────────────────────────────────────────────────────────────

def checkin_to_spot(payload: Union[dict, List[dict]], bulk: bool = False) -> dict:
    """
    bulk=True  → convert all checkins, return a FeatureCollection.
    bulk=False → require exactly one checkin, return a bare Feature.
    """
    fieldsites = multiple_checkin_to_fieldsite(payload)
    if bulk:
        return fieldsite_to_spot(fieldsites, bulk=True)
    if len(fieldsites) != 1:
        raise HTTPException(status_code=400, detail="bulk=false requires exactly one valid checkin.")
    return _fieldsite_to_spot_single(fieldsites[0])


# ── Spot ↔ Checkin ────────────────────────────────────────────────────────────

def spot_to_checkin(spot: Union[dict, List[dict]], bulk: bool = False) -> Union[dict, list[dict]]:
    """
    bulk=True  → convert all spots, return a list of checkins.
    bulk=False → require exactly one spot, return a single checkin dict.
    """
    if bulk:
        if isinstance(spot, list):
            if spot and isinstance(spot[0], dict) and "location" in spot[0]:
                return multiple_fieldsite_to_rockd_checkin(spot)
            return multiple_fieldsite_to_rockd_checkin(multiple_spot_to_fieldsite(spot))
        if isinstance(spot, dict) and "location" in spot:
            checkins = multiple_fieldsite_to_rockd_checkin([spot])
            return checkins[0] if len(checkins) == 1 else checkins
        is_single = isinstance(spot, dict) and (
            spot.get("type") == "Feature" or
            (spot.get("type") == "FeatureCollection" and len(spot.get("features") or []) == 1)
        )
        checkins = multiple_fieldsite_to_rockd_checkin(multiple_spot_to_fieldsite(spot))
        return checkins[0] if is_single and len(checkins) == 1 else checkins
    fieldsites = multiple_spot_to_fieldsite(spot)
    if len(fieldsites) != 1:
        raise HTTPException(status_code=400, detail="bulk=false requires exactly one valid spot.")
    return fieldsite_to_rockd_checkin(fieldsites[0])