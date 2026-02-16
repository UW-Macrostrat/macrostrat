from typing import Any, Iterable, List, Optional, Union

import dotenv
import httpx
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from slugify import slugify
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import NoResultFound, NoSuchTableError

dotenv.load_dotenv()

from datetime import datetime, timezone
from typing import Optional

from api.database import (
    get_async_session,
    get_engine,
    get_table,
    patch_sources_sub_table,
    select_sources_sub_table,
)
from api.models.field_site import (
    BeddingFacing,
    FieldSite,
    Location,
    Observation,
    Photo,
    PlanarOrientation,
)
from api.query_parser import ParserException
from api.routes.security import has_access

convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)


# _____________________HELPERS_________________________________
def _dt_to_ms(dt: Optional[datetime]) -> Optional[int]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _dt_to_iso_z(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_checkin_date(dt: Optional[datetime]) -> Optional[str]:
    """Match example Rockd checkin date strings like 'October 19, 2023'."""
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%B %d, %Y")


def _iter_spot_features(payload: Any) -> Iterable[dict]:
    """
    Yield GeoJSON Feature dicts from:
    - FeatureCollection
    - Feature
    - list[FeatureCollection|Feature]
    - list[Feature] (rare but convenient)
    """
    if payload is None:
        return
    items = payload if isinstance(payload, list) else [payload]

    for item in items:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        # A single Feature
        if t == "Feature":
            yield item
            continue
        # A FeatureCollection
        if t == "FeatureCollection":
            feats = item.get("features") or []
            if isinstance(feats, list):
                for f in feats:
                    if isinstance(f, dict) and f.get("type") == "Feature":
                        yield f
            continue
        feats = item.get("features")
        if isinstance(feats, list):
            for f in feats:
                if isinstance(f, dict) and f.get("type") == "Feature":
                    yield f


def _iter_checkins(payload: Any) -> Iterable[dict]:
    """
    Yield checkin dicts from:
      - dict (single checkin)
      - list[dict] (multiple checkins)
    """
    if payload is None:
        return
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if isinstance(item, dict):
            yield item


def _parse_date_time(x: Optional[str]) -> Optional[datetime]:
    if not x:
        return None
    try:
        return datetime.fromisoformat(x.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(x, "%B %d, %Y").replace(tzinfo=timezone.utc)
        except Exception:
            return None


def _to_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


# normalize and require lat/lngs
def _valid_coords(lat, lng) -> bool:
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0


def _all_planars_from_spot(props) -> list[PlanarOrientation]:
    """Return all planar orientations with numeric strike & dip in StraboSpot props."""
    orientation = props.get("orientation_data")
    if not isinstance(orientation, list):
        return []
    out = []
    for item in orientation:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "planar_orientation":
            strike = _to_float(item.get("strike"))
            dip = _to_float(item.get("dip"))
            if strike is not None and dip is not None:
                out.append(
                    PlanarOrientation(
                        strike=strike, dip=dip, facing=BeddingFacing.upright
                    )
                )
    return out


def _all_planars_from_checkin(checkin) -> list[PlanarOrientation]:
    """Return all observations with numeric strike & dip in Rockd checkin."""
    obs = checkin.get("observations")
    if not isinstance(obs, list):
        return []
    out = []
    for o in obs:
        if not isinstance(o, dict):
            continue
        orientation = o.get("orientation") or {}
        strike = _to_float(orientation.get("strike"))
        dip = _to_float(orientation.get("dip"))
        if strike is not None and dip is not None:
            out.append(
                PlanarOrientation(strike=strike, dip=dip, facing=BeddingFacing.upright)
            )
    return out


def _all_planars_from_fieldsite(fs: FieldSite) -> list[PlanarOrientation]:
    """Return all PlanarOrientations in FieldSite.observations."""
    return [
        ob.data
        for ob in (fs.observations or [])
        if isinstance(getattr(ob, "data", None), PlanarOrientation)
    ]


# _____________________________SPOT - FS - CHECKIN_________________________________
def spot_to_fieldsite(feat) -> FieldSite:
    props = feat.get("properties", {}) or {}
    geom = feat.get("geometry", {}) or {}
    # require id
    sid = props.get("id")
    if sid is None:
        raise ValueError("Missing spot properties.id")
    lat = props.get("lat")
    lng = props.get("lng")
    if (lat is None or lng is None) and geom.get("type") == "Point":
        coords = geom.get("coordinates", []) or []
        if len(coords) >= 2:
            lng = coords[0] if lng is None else lng
            lat = coords[1] if lat is None else lat
    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Spot feature")

    photos = []
    images = props.get("images")
    if isinstance(images, list) and images:
        img = images[0] or {}
        pid = img.get("id")
        if pid is not None:
            photos.append(
                Photo(
                    id=int(pid),
                    url=f"rockd://photo/{pid}",
                    width=int(img.get("width", 0) or 0),
                    height=int(img.get("height", 0) or 0),
                    checksum="",
                )
            )
    observations = [Observation(data=p) for p in _all_planars_from_spot(props)]
    created = _parse_date_time(props.get("time") or props.get("date")) or datetime.now(
        timezone.utc
    )
    mt = props.get("modified_timestamp")
    if mt is not None:
        try:
            updated = datetime.fromtimestamp(float(mt) / 1000.0, tz=timezone.utc)
        except Exception:
            updated = created
    else:
        updated = created
    return FieldSite(
        id=sid,
        location=Location(latitude=float(lat), longitude=float(lng)),
        created=created,
        updated=updated,
        notes=props.get("notes"),
        photos=photos,
        observations=observations,
    )


def multiple_spot_to_fieldsite(
    payload: Union[dict, List[dict]] = Body(...)
) -> List[FieldSite]:
    """
    Accept:
      - FeatureCollection with many spots (your example)
      - a single Feature
      - a list of FeatureCollections/Features
    Return a FieldSite for each qualifying Point feature.
    """
    out: list[FieldSite] = []
    for feat in _iter_spot_features(payload):
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        # Only Point features become FieldSites
        if geom.get("type") != "Point":
            continue
        # Skip "on image" annotation points
        if props.get("image_basemap") is not None:
            continue
        # Require spot id
        if props.get("id") is None:
            continue
        # spot_to_fieldsite will validate coords (from props or geometry)
        try:
            out.append(spot_to_fieldsite(feat))
        except Exception:
            continue
    return out


def spot_to_checkin(
    spot: Union[dict, List[dict]] = Body(...)
) -> Union[dict, list[dict]]:
    """Pipeline: Spot JSON (FeatureCollections) or FieldSites -> Checkin(s).
    Output rule:
    - dict output only when the input is a single object representing a single spot/fieldsite
      (Feature OR FeatureCollection with exactly 1 feature OR single FieldSite dict)
      AND exactly one checkin is produced.
    - otherwise list output
    """
    # multiple fieldsites
    if isinstance(spot, list):
        if spot and isinstance(spot[0], dict) and "location" in spot[0]:
            return multiple_fieldsite_to_rockd_checkin(spot)
        fieldsites = multiple_spot_to_fieldsite(spot)
        return multiple_fieldsite_to_rockd_checkin(fieldsites)
    # single fieldsite object
    if isinstance(spot, dict) and "location" in spot:
        checkins = multiple_fieldsite_to_rockd_checkin([spot])
        return checkins[0] if len(checkins) == 1 else checkins
    # determine whether this is a single spot
    is_single_spot_payload = False
    if isinstance(spot, dict):
        t = spot.get("type")
        if t == "Feature":
            is_single_spot_payload = True
        elif t == "FeatureCollection":
            feats = spot.get("features")
            if isinstance(feats, list) and len(feats) == 1:
                is_single_spot_payload = True
    fieldsites = multiple_spot_to_fieldsite(spot)
    checkins = multiple_fieldsite_to_rockd_checkin(fieldsites)
    if is_single_spot_payload and len(checkins) == 1:
        return checkins[0]
    return checkins


# ___________________________________CHECKIN - FS - SPOT____________________________________
def checkin_to_fieldsite(checkin: dict) -> FieldSite:
    """
    Convert Rockd checkin JSON dict -> FieldSite.

    Required:
      - checkin_id
      - lat/lng
    """
    if not isinstance(checkin, dict):
        raise ValueError("Checkin must be a dict")
    cid = checkin.get("checkin_id")
    if cid is None:
        raise ValueError("Missing checkin_id")
    lat, lng = checkin.get("lat"), checkin.get("lng")
    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Checkin")
    photos: list[Photo] = []
    pid = checkin.get("photo")
    if isinstance(pid, int):
        photos.append(
            Photo(
                id=int(pid),
                url=f"rockd://photo/{pid}",
                width=0,
                height=0,
                checksum="",
            )
        )

    observations = [Observation(data=p) for p in _all_planars_from_checkin(checkin)]
    created = _parse_date_time(checkin.get("created")) or datetime.now(timezone.utc)

    updated = (
        _parse_date_time(checkin.get("updated"))
        or _parse_date_time(checkin.get("added"))
        or created
    )

    return FieldSite(
        id=int(cid),
        location=Location(latitude=float(lat), longitude=float(lng)),
        created=created,
        updated=updated,
        notes=checkin.get("notes"),
        photos=photos,
        observations=observations,
    )


def multiple_checkin_to_fieldsite(
    payload: Union[dict, List[dict]] = Body(...)
) -> List[FieldSite]:
    """Convert single checkin dict OR list of checkins -> list[FieldSite]."""
    out: list[FieldSite] = []
    for c in _iter_checkins(payload):
        try:
            out.append(checkin_to_fieldsite(c))
        except Exception:
            continue
    return out


def fieldsite_to_rockd_checkin(fs: FieldSite) -> dict:
    """
    Convert FieldSite -> Rockd checkin JSON (based on your example structure),
    but ALSO include spot_id for compatibility with spot-based pipelines.
    """
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)
    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created
    d: dict = {
        "checkin_id": fs.id,
        "spot_id": fs.id,
        "notes": fs.notes,
        "lat": fs.location.latitude,
        "lng": fs.location.longitude,
        "created": _dt_to_iso_z(created),
        "updated": _dt_to_iso_z(updated),
    }
    if fs.photos:
        d["photo"] = fs.photos[0].id
    d["observations"] = [
        {"orientation": {"strike": float(p.strike), "dip": float(p.dip)}}
        for p in _all_planars_from_fieldsite(fs)
    ]
    return d


def multiple_fieldsite_to_rockd_checkin(
    fieldsites: Union[list[FieldSite], list[dict]] = Body(...)
) -> list[dict]:
    """Convert list[FieldSite] (or list[dict]) -> list[Rockd checkin dict]."""
    out: list[dict] = []
    for fs in fieldsites or []:
        try:
            if not isinstance(fs, FieldSite):
                fs = FieldSite(**fs)
            out.append(fieldsite_to_rockd_checkin(fs))
        except Exception:
            continue
    return out


def fieldsite_to_spot(fs: FieldSite) -> dict:
    """
    Convert a single FieldSite -> VALID StraboSpot spot payload.

    IMPORTANT: For posting, StraboSpot expects a FeatureCollection (not a bare Feature).
    So this returns:
      {"type": "FeatureCollection", "features": [<Feature>]}
    """
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)
    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created
    feat: dict = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [fs.location.longitude, fs.location.latitude],
        },
        "properties": {
            "id": fs.id,
            "notes": fs.notes,
            "time": created.isoformat().replace("+00:00", "Z"),
            "date": created.isoformat().replace("+00:00", "Z"),
            "modified_timestamp": _dt_to_ms(updated),
            "lat": fs.location.latitude,
            "lng": fs.location.longitude,
        },
    }
    if fs.photos:
        p = fs.photos[0]
        feat["properties"]["images"] = [
            {
                "id": int(p.id),
                "width": int(getattr(p, "width", 0) or 0),
                "height": int(getattr(p, "height", 0) or 0),
                "title": "",
                "image_type": "photo",
            }
        ]
    planars = _all_planars_from_fieldsite(fs)
    if planars:
        feat["properties"]["orientation_data"] = [
            {
                "type": "planar_orientation",
                "strike": float(p.strike),
                "dip": float(p.dip),
            }
            for p in planars
        ]
    return {"type": "FeatureCollection", "features": [feat]}


def multiple_fieldsite_to_spot(fieldsites: list[FieldSite]) -> dict:
    """Convert many FieldSites -> one StraboSpot FeatureCollection with many Features."""
    features: list[dict] = []
    for fs in fieldsites or []:
        try:
            fc = fieldsite_to_spot(fs)  # FeatureCollection with 1 feature
            f = (fc.get("features") or [None])[0]
            if isinstance(f, dict):
                features.append(f)
        except Exception:
            continue
    return {"type": "FeatureCollection", "features": features}


def checkin_to_spot(payload: Union[dict, List[dict]] = Body(...)) -> dict:
    """
    Convert:
      - single checkin dict
      - list of checkin dicts
    -> VALID StraboSpot FeatureCollection (single or multi-spot).
    """
    fieldsites = multiple_checkin_to_fieldsite(payload)
    if len(fieldsites) == 1:
        return fieldsite_to_spot(fieldsites[0])
    return multiple_fieldsite_to_spot(fieldsites)


# _________________________________API ROUTE___________________________________
@convert_router.post("/field-site")
async def convert_field_site(
    payload: Union[dict, List[dict]] = Body(...),
    in_: str = Query(..., alias="in"),
    out: str = Query(..., alias="out"),
) -> Any:
    key = (in_.lower(), out.lower())
    if key == ("spot", "fieldsite"):
        return multiple_spot_to_fieldsite(payload)
    if key == ("checkin", "fieldsite"):
        return multiple_checkin_to_fieldsite(payload)
    if key == ("fieldsite", "checkin"):
        if isinstance(payload, list):
            if len(payload) == 1:
                return fieldsite_to_rockd_checkin(payload[0])
            return multiple_fieldsite_to_rockd_checkin(payload)
        return fieldsite_to_rockd_checkin(payload)
    if key == ("fieldsite", "spot"):
        if isinstance(payload, list):
            return multiple_fieldsite_to_spot(payload)
        return fieldsite_to_spot(payload)
    if key == ("checkin", "spot"):
        return checkin_to_spot(payload)
    if key == ("spot", "checkin"):
        return spot_to_checkin(payload)
    raise HTTPException(
        status_code=400,
        detail="Unsupported conversion. Use in=[spot|fieldsite|checkin], out=[fieldsite|checkin|spot].",
    )
