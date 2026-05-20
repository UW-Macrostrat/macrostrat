"""
This file contains all the functions that convert data between three formats:
  Rockd checkins       Location data collected in the Rockd mobile app
  StraboSpot spots     Location data used in the StraboSpot field mapping app
  FieldSite objects    The internal neutral format used by this API

The conversions flow through FieldSite as a common middle step:
  Rockd checkin  becomes a FieldSite  which becomes a StraboSpot spot
  StraboSpot spot  becomes a FieldSite  which becomes a Rockd checkin

Helper functions at the bottom of this file handle small reusable tasks
like validating coordinates or parsing dates.
"""

from typing import Any, Iterable, List, Optional, Union
from datetime import datetime, timezone
import dotenv

dotenv.load_dotenv()

from . import (
    BeddingFacing,
    FieldSite,
    Location,
    Observation,
    Photo,
    PlanarOrientation,
)
from fastapi import HTTPException


# ── Spot to FieldSite ─────────────────────────────────────────────────────────


def spot_to_fieldsite(feat: dict) -> FieldSite:
    """
    Converts a single StraboSpot GeoJSON Feature into a FieldSite object.

    A StraboSpot Feature looks like standard GeoJSON with a properties block
    that holds the spot details and a geometry block that holds the coordinates.
    This function reads those blocks and builds a FieldSite from the data it finds.

    Raises a ValueError if the spot is missing an ID or valid coordinates.
    """
    props = feat.get("properties") or {}
    geom = feat.get("geometry") or {}

    # Every spot must have an ID so we can track it later
    sid = props.get("id")
    if sid is None:
        raise ValueError("Missing spot properties.id")

    # Try to get coordinates from the properties block first
    lat, lng = props.get("lat"), props.get("lng")

    # If lat or lng is missing from properties, fall back to the GeoJSON geometry block
    # GeoJSON stores coordinates as [longitude, latitude] so index 0 is lng and 1 is lat
    if (lat is None or lng is None) and geom.get("type") == "Point":
        coords = geom.get("coordinates") or []
        if len(coords) >= 2:
            lng = coords[0] if lng is None else lng
            lat = coords[1] if lat is None else lat

    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Spot feature")

    # Build the photo list from the first image in the spot if one exists
    photos = []
    images = props.get("images") or []
    if images and (img := images[0] or {}) and img.get("id") is not None:
        photos.append(
            Photo(
                id=int(img["id"]),
                url="https://dev.rockd.org/api/v2/protected/image",
                width=int(img.get("width") or 0),
                height=int(img.get("height") or 0),
                checksum="",
            )
        )

    # Parse the creation time from the spot, defaulting to right now if missing
    created = _parse_date_time(props.get("time") or props.get("date")) or datetime.now(
        timezone.utc
    )

    # The modified timestamp in StraboSpot is stored as milliseconds since epoch
    mt = props.get("modified_timestamp")
    updated = (
        datetime.fromtimestamp(float(mt) / 1000, tz=timezone.utc)
        if mt is not None
        else created
    )

    return FieldSite(
        id=sid,
        location=Location(latitude=float(lat), longitude=float(lng)),
        created=created,
        updated=updated,
        # Use name as the note if notes is not present
        notes=props.get("name") or props.get("notes"),
        photos=photos,
        observations=[Observation(data=p) for p in _all_planars_from_spot(props)],
    )


def multiple_spot_to_fieldsite(payload: Union[dict, List[dict]]) -> List[FieldSite]:
    """
    Converts a StraboSpot payload containing one or many spots into a list of FieldSites.

    The payload can be a FeatureCollection, a single Feature, or a list of either.
    Only Point geometry features are converted because FieldSite represents a single location.
    Features that are image annotations (image basemap features) are skipped.
    Features without an ID are also skipped.
    Any feature that fails to convert is silently skipped rather than stopping the whole batch.
    """
    out = []
    for feat in _iter_spot_features(payload):
        props, geom = feat.get("properties") or {}, feat.get("geometry") or {}

        # Skip non-point features, image annotations, and features without an ID
        if (
            geom.get("type") != "Point"
            or props.get("image_basemap") is not None
            or props.get("id") is None
        ):
            continue

        try:
            out.append(spot_to_fieldsite(feat))
        except Exception:
            # Skip this feature and continue with the rest
            pass

    return out


# ── Checkin to FieldSite ──────────────────────────────────────────────────────


def checkin_to_fieldsite(checkin: dict) -> FieldSite:
    """
    Converts a single Rockd checkin dictionary into a FieldSite object.

    A Rockd checkin holds a location, optional notes, an optional photo ID,
    and optional strike and dip measurements from the Rockd app.
    This function reads those fields and builds a FieldSite from them.

    Raises a ValueError if the checkin is missing a checkin_id or valid coordinates.
    """
    if not isinstance(checkin, dict):
        raise ValueError("Checkin must be a dict")

    cid = checkin.get("checkin_id")
    if cid is None:
        raise ValueError("Missing checkin_id")

    lat, lng = checkin.get("lat"), checkin.get("lng")
    if not _valid_coords(lat, lng):
        raise ValueError("Invalid or missing lat/lng for Checkin")

    # Build a photo reference if the checkin has a photo ID
    photos = []
    pid = checkin.get("photo")
    if isinstance(pid, int):
        photos.append(
            Photo(id=pid, url=f"rockd://photo/{pid}", width=0, height=0, checksum="")
        )

    # Parse creation time, defaulting to now if missing
    created = _parse_date_time(checkin.get("created")) or datetime.now(timezone.utc)

    # Try multiple date fields for the updated time, falling back to created
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
        observations=[Observation(data=p) for p in _all_planars_from_checkin(checkin)],
    )


def multiple_checkin_to_fieldsite(payload: Union[dict, List[dict]]) -> List[FieldSite]:
    """
    Converts one or many Rockd checkins into a list of FieldSite objects.

    Accepts either a single checkin dict or a list of checkin dicts.
    Any checkin that fails to convert is silently skipped.
    """
    out = []
    for c in payload if isinstance(payload, list) else [payload]:
        if isinstance(c, dict):
            try:
                out.append(checkin_to_fieldsite(c))
            except Exception:
                pass
    return out


# ── FieldSite to Checkin ──────────────────────────────────────────────────────


def fieldsite_to_rockd_checkin(fs: FieldSite) -> dict:
    """
    Converts a single FieldSite object into a Rockd checkin dictionary.

    The output format matches what the Rockd create-edit-checkin API expects.
    Observations with strike and dip measurements are included as orientation data.
    The spot ID field links this checkin back to its originating StraboSpot spot.
    """
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)

    created = fs.created or datetime.now(timezone.utc)

    # Capture the current time in milliseconds to use as a unique identifier
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    d = {
        "notes": (fs.notes or "").strip(),
        "rating": 0,
        "lat": float(fs.location.latitude),
        "lng": float(fs.location.longitude),
        "created": _dt_to_iso_z(created),
        # spot_id links this Rockd checkin to its counterpart in StraboSpot
        "spot_id": int(fs.id) if fs.id is not None else None,
        # new_checkin_id is a temporary client-side ID used by Rockd during creation
        "new_checkin_id": str(now_ms),
    }

    # Attach the photo filename if the site has a photo
    if fs.photos:
        d["photo"] = f"{int(fs.photos[0].id)}.jpg"

    # Build the observations list from any planar orientation measurements on this site
    d["observations"] = [
        {
            # Each observation gets a unique ID combining a prefix, index, and timestamp
            "new_obs_id": f"interchange_obs_{i}_{now_ms}",
            "rocks": {
                "strat_name": {},
                "liths": [],
                "interval": {},
                "notes": "",
                "map_unit": {},
            },
            "minerals": {"minerals": [], "notes": ""},
            "orientation": {
                "strike": _to_float(p.strike),
                "strikestd": None,
                "dip": _to_float(p.dip),
                "dipstd": None,
                "dip_dir": None,
                "feature": {},
                "notes": "",
                "trend": None,
                "trendstd": None,
                "plunge": None,
                "plungestd": None,
            },
            "fossils": {"taxa": [], "notes": ""},
        }
        for i, p in enumerate(_all_planars_from_fieldsite(fs))
    ]

    return d


def multiple_fieldsite_to_rockd_checkin(
    fieldsites: Union[list[FieldSite], list[dict]],
) -> list[dict]:
    """
    Converts a list of FieldSite objects into a list of Rockd checkin dictionaries.

    Each item in the list can be either a FieldSite object or a plain dictionary.
    Plain dictionaries are coerced into FieldSite objects before conversion.
    Any item that fails to convert is silently skipped.
    """
    out = []
    for fs in fieldsites or []:
        try:
            # Coerce plain dicts into FieldSite objects if needed
            if not isinstance(fs, FieldSite):
                fs = FieldSite(**fs)
            out.append(fieldsite_to_rockd_checkin(fs))
        except Exception:
            pass
    return out


# ── FieldSite to Spot ─────────────────────────────────────────────────────────


def _fieldsite_to_spot_feature(fs: FieldSite) -> dict:
    """
    Builds a StraboSpot GeoJSON Feature from a FieldSite.

    This produces the FeatureCollection compatible format where the feature
    lives inside a features array. Use this when posting to StraboSpot bulk endpoints
    or when the caller expects a FeatureCollection wrapper.

    The coordinates are stored as [longitude, latitude] to match the GeoJSON standard.
    """
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)

    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created

    feat = {
        "type": "Feature",
        # GeoJSON requires coordinates in [longitude, latitude] order
        "geometry": {
            "type": "Point",
            "coordinates": [fs.location.longitude, fs.location.latitude],
        },
        "properties": {
            "id": fs.id,
            "notes": fs.notes,
            "time": _dt_to_iso_z(created),
            "date": _dt_to_iso_z(created),
            "modified_timestamp": _dt_to_ms(updated),
            "lat": fs.location.latitude,
            "lng": fs.location.longitude,
        },
    }

    # Only add the images block if there are photos to include
    if fs.photos:
        feat["properties"]["images"] = [
            {
                "id": int(p.id),
                "width": int(getattr(p, "width", 0) or 0),
                "height": int(getattr(p, "height", 0) or 0),
                "title": "",
                "image_type": "photo",
            }
            for p in fs.photos
        ]

    # Only add the orientation block if there are measurements to include
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

    return feat


def _fieldsite_to_spot_single(fs: FieldSite) -> dict:
    """
    Builds a bare StraboSpot Feature from a FieldSite for use with single spot endpoints.

    This format is slightly different from the FeatureCollection format.
    It includes extra fields like samples and name that the single spot API expects.
    It also uses a more detailed orientation format that matches what StraboSpot stores.
    """
    if not isinstance(fs, FieldSite):
        fs = FieldSite(**fs)

    created = fs.created or datetime.now(timezone.utc)
    updated = fs.updated or created

    feat = {
        "type": "Feature",
        "properties": {
            "images": [],
            "time": _dt_to_iso_z(created),
            "id": fs.id,
            "orientation_data": [],
            "modified_timestamp": _dt_to_ms(updated),
            "date": _dt_to_iso_z(created),
            "samples": [],
            # StraboSpot uses name rather than notes for the display label
            "name": fs.notes or "",
        },
        "geometry": {
            "type": "Point",
            # GeoJSON requires coordinates in [longitude, latitude] order
            "coordinates": [fs.location.longitude, fs.location.latitude],
        },
    }

    # Replace the empty images list with actual photo data if available
    if fs.photos:
        feat["properties"]["images"] = [
            {
                "height": int(getattr(p, "height", 0) or 0),
                "id": int(p.id),
                "annotated": False,
                "title": "",
                "width": int(getattr(p, "width", 0) or 0),
                "caption": "",
            }
            for p in fs.photos
        ]

    # Replace the empty orientation list with actual measurements if available
    planars = _all_planars_from_fieldsite(fs)
    if planars:
        feat["properties"]["orientation_data"] = [
            {
                "dip_direction": None,
                "strike": _to_float(p.strike),
                "dip": _to_float(p.dip),
                # Use the facing value from the model, defaulting to upright
                "facing": (
                    p.facing.value
                    if getattr(p, "facing", None) is not None
                    else "upright"
                ),
                "orientation_type": "planar_orientation",
            }
            for p in planars
        ]

    return feat


def fieldsite_to_spot(
    payload: Union[FieldSite, dict, List], bulk: bool = False
) -> dict:
    """
    Converts one or many FieldSite objects into a StraboSpot FeatureCollection.

    When bulk is False, the payload should be a single FieldSite and the result
    will be a FeatureCollection containing that one feature.

    When bulk is True, the payload should be a list of FieldSites and the result
    will be a FeatureCollection containing all of them as features.
    Items that fail to convert are silently skipped in bulk mode.
    """
    if bulk:
        features = []
        for fs in payload or []:
            try:
                features.append(_fieldsite_to_spot_feature(fs))
            except Exception:
                pass
        return {"type": "FeatureCollection", "features": features}

    # Single mode: wrap the one feature in a FeatureCollection
    return {
        "type": "FeatureCollection",
        "features": [_fieldsite_to_spot_feature(payload)],
    }


# ── Checkin to Spot ───────────────────────────────────────────────────────────


def checkin_to_spot(payload: Union[dict, List[dict]], bulk: bool = False) -> dict:
    """
    Converts Rockd checkins directly into StraboSpot spot format.

    This pipelines through FieldSite as an intermediate step:
      Rockd checkin  becomes FieldSite  becomes StraboSpot spot

    When bulk is False, exactly one checkin must be provided and the result
    is a bare Feature in the single spot format.

    When bulk is True, any number of checkins can be provided and the result
    is a FeatureCollection in the multi spot format.
    """
    # Convert all checkins to FieldSite objects first
    fieldsites = multiple_checkin_to_fieldsite(payload)

    if bulk:
        return fieldsite_to_spot(fieldsites, bulk=True)

    # In single mode, require exactly one valid checkin
    if len(fieldsites) != 1:
        raise HTTPException(
            status_code=400, detail="bulk=false requires exactly one valid checkin."
        )

    # Use the single spot format for the output
    return _fieldsite_to_spot_single(fieldsites[0])


# ── Spot to Checkin ───────────────────────────────────────────────────────────


def spot_to_checkin(
    spot: Union[dict, List[dict]], bulk: bool = False
) -> Union[dict, list[dict]]:
    """
    Converts StraboSpot spots directly into Rockd checkin format.

    This pipelines through FieldSite as an intermediate step:
      StraboSpot spot  becomes FieldSite  becomes Rockd checkin

    When bulk is False, exactly one spot must be provided and the result
    is a single checkin dictionary.

    When bulk is True, any number of spots can be provided.
    The function also handles the case where the caller already provides
    FieldSite objects instead of raw spot GeoJSON.
    """
    if bulk:
        # If the input is already a list of FieldSite-like dicts, convert directly
        if isinstance(spot, list):
            if spot and isinstance(spot[0], dict) and "location" in spot[0]:
                return multiple_fieldsite_to_rockd_checkin(spot)
            return multiple_fieldsite_to_rockd_checkin(multiple_spot_to_fieldsite(spot))

        # If the input is a single FieldSite-like dict, wrap it in a list first
        if isinstance(spot, dict) and "location" in spot:
            checkins = multiple_fieldsite_to_rockd_checkin([spot])
            return checkins[0] if len(checkins) == 1 else checkins

        # Detect whether the input represents a single spot so we can unwrap the result
        is_single = isinstance(spot, dict) and (
            spot.get("type") == "Feature"
            or (
                spot.get("type") == "FeatureCollection"
                and len(spot.get("features") or []) == 1
            )
        )
        checkins = multiple_fieldsite_to_rockd_checkin(multiple_spot_to_fieldsite(spot))
        return checkins[0] if is_single and len(checkins) == 1 else checkins

    # In single mode, require exactly one valid spot
    fieldsites = multiple_spot_to_fieldsite(spot)
    if len(fieldsites) != 1:
        raise HTTPException(
            status_code=400, detail="bulk=false requires exactly one valid spot."
        )

    return fieldsite_to_rockd_checkin(fieldsites[0])


# ── Helper functions ──────────────────────────────────────────────────────────


def _ensure_utc(dt: datetime) -> datetime:
    """
    Makes sure a datetime value has timezone information set to UTC.
    If the datetime has no timezone at all, it is assumed to be UTC and labeled as such.
    """
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _dt_to_ms(dt: Optional[datetime]) -> Optional[int]:
    """
    Converts a datetime to milliseconds since the Unix epoch (January 1 1970).
    Returns None if no datetime is provided.
    This format is commonly used by JavaScript and mobile apps to store timestamps.
    """
    return int(_ensure_utc(dt).timestamp() * 1000) if dt else None


def _dt_to_iso_z(dt: Optional[datetime]) -> Optional[str]:
    """
    Converts a datetime to an ISO 8601 string ending in Z to indicate UTC.
    For example 2024-03-15T10:30:00Z.
    Returns None if no datetime is provided.
    The Z suffix is a widely recognized shorthand for the UTC timezone.
    """
    return (
        _ensure_utc(dt).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if dt
        else None
    )


def _to_float(v) -> Optional[float]:
    """
    Safely converts a value to a float.
    Returns None if the value is None or cannot be converted.
    This avoids crashes when a field contains an unexpected data type.
    """
    try:
        return None if v is None else float(v)
    except Exception:
        return None


def _valid_coords(lat, lng) -> bool:
    """
    Checks whether latitude and longitude values are within the valid ranges.
    Latitude must be between -90 and 90 and longitude must be between -180 and 180.
    Returns False if either value is missing or outside the valid range.
    """
    lat, lng = _to_float(lat), _to_float(lng)
    return (
        lat is not None and lng is not None and -90 <= lat <= 90 and -180 <= lng <= 180
    )


def _parse_date_time(x: Optional[str]) -> Optional[datetime]:
    """
    Tries to convert a date string into a datetime object.
    Supports ISO 8601 format like 2024-03-15T10:30:00Z
    and plain English format like March 15 2024.
    Returns None if the string is empty or does not match either format.
    """
    if not x:
        return None

    for parser in (
        # Try the standard ISO format first since it is more common
        lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
        # Fall back to the human readable format used in some Rockd fields
        lambda s: datetime.strptime(s, "%B %d, %Y").replace(tzinfo=timezone.utc),
    ):
        try:
            return parser(x)
        except Exception:
            pass

    return None


def _iter_spot_features(payload: Any) -> Iterable[dict]:
    """
    Walks through a payload and yields individual GeoJSON Feature dicts.

    The payload can be a single Feature, a FeatureCollection, a list of Features,
    or a list of FeatureCollections. This generator handles all those cases
    so the calling code does not need to worry about the shape of the input.
    """
    for item in payload if isinstance(payload, list) else [payload]:
        if not isinstance(item, dict):
            continue

        t = item.get("type")

        if t == "Feature":
            # The item itself is a feature so yield it directly
            yield item
        elif t == "FeatureCollection" or "features" in item:
            # The item is a collection so yield each feature inside it
            yield from (
                f
                for f in (item.get("features") or [])
                if isinstance(f, dict) and f.get("type") == "Feature"
            )


def _planars(items: list, strike_key: str, dip_key: str) -> list[PlanarOrientation]:
    """
    Extracts PlanarOrientation objects from a list of dictionaries.

    Each dictionary is checked for the named strike and dip keys.
    Items that are missing either value are skipped.
    This is a reusable helper called by the spot and checkin specific planar functions below.
    """
    out = []
    for item in items or []:
        if not isinstance(item, dict):
            continue

        s, d = _to_float(item.get(strike_key)), _to_float(item.get(dip_key))

        # Only add an orientation if both strike and dip are present and numeric
        if s is not None and d is not None:
            out.append(PlanarOrientation(strike=s, dip=d, facing=BeddingFacing.upright))

    return out


def _all_planars_from_spot(props) -> list[PlanarOrientation]:
    """
    Extracts all planar orientation measurements from a StraboSpot feature's properties.

    StraboSpot stores orientations in a list called orientation_data.
    Only items with type planar_orientation are included here.
    Linear orientations and other types are ignored.
    """
    return _planars(
        [
            i
            for i in (props.get("orientation_data") or [])
            if isinstance(i, dict) and i.get("type") == "planar_orientation"
        ],
        "strike",
        "dip",
    )


def _all_planars_from_checkin(checkin) -> list[PlanarOrientation]:
    """
    Extracts all planar orientation measurements from a Rockd checkin.

    Rockd stores orientations inside a list called observations.
    Each observation has an orientation block that may contain strike and dip values.
    This function collects all the orientation blocks and extracts the numeric values.
    """
    return _planars(
        [
            # Pull the orientation sub-dict from each observation
            o.get("orientation") or {}
            for o in (checkin.get("observations") or [])
            if isinstance(o, dict)
        ],
        "strike",
        "dip",
    )


def _all_planars_from_fieldsite(fs: FieldSite) -> list[PlanarOrientation]:
    """
    Extracts all PlanarOrientation objects stored in a FieldSite's observations list.

    A FieldSite can hold many types of observations. This function filters
    to only those whose data field is a PlanarOrientation instance.
    """
    return [
        ob.data
        for ob in (fs.observations or [])
        if isinstance(getattr(ob, "data", None), PlanarOrientation)
    ]