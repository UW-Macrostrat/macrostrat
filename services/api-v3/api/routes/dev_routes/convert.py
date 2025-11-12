from typing import Any, Iterable, List, Union

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

# helpers


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


def _first_planar_from_spot(props) -> Optional[PlanarOrientation]:
    """Find first planar orientation with numeric strike & dip in StraboSpot props."""
    orientation = props.get("orientation_data")
    if not isinstance(orientation, list):
        return None
    for item in orientation:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "planar_orientation":
            strike = _to_float(item.get("strike"))
            dip = _to_float(item.get("dip"))
            if strike is not None and dip is not None:
                return PlanarOrientation(
                    strike=strike, dip=dip, facing=BeddingFacing.upright
                )
    return None


def _first_planar_from_checkin(checkin) -> Optional[PlanarOrientation]:
    """Find first observation with numeric strike & dip in Rockd checkin."""
    obs = checkin.get("observations")
    if not isinstance(obs, list):
        return None
    for o in obs:
        if not isinstance(o, dict):
            continue
        orientation = o.get("orientation") or {}
        strike = _to_float(orientation.get("strike"))
        dip = _to_float(orientation.get("dip"))
        if strike is not None and dip is not None:
            return PlanarOrientation(
                strike=strike, dip=dip, facing=BeddingFacing.upright
            )
    return None


def _first_planar_from_fieldsite(fs: FieldSite) -> Optional[PlanarOrientation]:
    """Return first PlanarOrientation in FieldSite.observations."""
    for ob in fs.observations or []:
        data = getattr(ob, "data", None)
        if isinstance(data, PlanarOrientation):
            return data
    return None


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
    observations: list[Observation] = []
    planar = _first_planar_from_spot(props)
    if planar:
        observations.append(Observation(data=planar))
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
    feat: Union[dict, List[dict]] = Body(...)
) -> List[FieldSite]:
    """
    Accept a single FeatureCollection or a list of FeatureCollections and
    return a FieldSite for each qualifying Point feature.
    """
    out: list[FieldSite] = []

    # normalize: allow a single FeatureCollection or a list of them
    collections = feat if isinstance(feat, list) else [feat]

    for coll in collections:
        if not isinstance(coll, dict) or coll.get("type") != "FeatureCollection":
            continue
        for f in coll.get("features", []) or []:
            props = f.get("properties", {}) or {}
            geom = f.get("geometry", {}) or {}
            if geom.get("type") != "Point":
                continue
            if props.get("image_basemap") is not None:
                continue
            if props.get("id") is None:
                continue
            coords = geom.get("coordinates", []) or []
            if len(coords) < 2 or not _valid_coords(coords[1], coords[0]):
                continue
            try:
                out.append(spot_to_fieldsite(f))
            except Exception:
                continue
    return out


def fieldsite_to_checkin(fs: FieldSite) -> dict:
    d = {
        "checkin_id": fs.id,
        "notes": fs.notes,
        "lat": fs.location.latitude,
        "lng": fs.location.longitude,
        "created": fs.created.isoformat(),
    }
    if fs.photos:
        d["photo"] = fs.photos[0].id
    planar = _first_planar_from_fieldsite(fs)
    if planar:
        d["observations"] = [
            {"orientation": {"strike": float(planar.strike), "dip": float(planar.dip)}}
        ]
    return d


def multiple_fieldsite_to_checkin(
    fieldsites: list[FieldSite] = Body(...),
) -> list[dict]:
    out: list[dict] = []
    for fs in fieldsites:
        try:
            if not isinstance(fs, FieldSite):
                fs = FieldSite(**fs)
            out.append(fieldsite_to_checkin(fs))
        except Exception:
            continue
    return out


def spot_to_checkin(spot: Union[dict, List[dict]] = Body(...)) -> list[dict]:
    """Pipeline: Spot JSON (FeatureCollection[s]) or FieldSite list -> Checkin list."""
    # If it's already a list of FieldSite-like dicts (has 'location'), skip the first hop
    if (
        isinstance(spot, list)
        and spot
        and isinstance(spot[0], dict)
        and "location" in spot[0]
    ):
        fieldsites: List[FieldSite] = spot  # already FieldSite-shaped
    else:
        # Convert FeatureCollection (or list of them) -> FieldSite list
        fieldsites = multiple_spot_to_fieldsite(spot)
    # Convert FieldSite list -> Checkin list
    return multiple_fieldsite_to_checkin(fieldsites)


@convert_router.post("/field-site")
async def convert_field_site(
    payload: Union[dict, List[dict]] = Body(...),
    in_: str = Query(..., alias="in"),
    out: str = Query(..., alias="out"),
) -> Any:
    """
    Unified converter:
    - ?in=spot&out=fieldsite   -> spot FeatureCollection(s) -> FieldSite
    - ?in=fieldsite&out=checkin -> FieldSite -> Checkin
    - ?in=spot&out=checkin     -> spot FeatureCollection(s) -> FieldSite -> Checkin
    """
    key = (in_.lower(), out.lower())
    if key == ("spot", "fieldsite"):
        return multiple_spot_to_fieldsite(payload)
    if key == ("fieldsite", "checkin"):
        return multiple_fieldsite_to_checkin(payload)
    if key == ("spot", "checkin"):
        return spot_to_checkin(payload)
    raise HTTPException(
        status_code=400,
        detail="Unsupported conversion. Use in=[spot|fieldsite], out=[fieldsite|checkin].",
    )
