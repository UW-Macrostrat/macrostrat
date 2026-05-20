from typing import Any, List, Optional, Union
from fastapi import APIRouter, Body, Header, HTTPException, Query
from .convert_utils import (
    checkin_to_spot,
    fieldsite_to_spot,
    multiple_checkin_to_fieldsite,
    multiple_fieldsite_to_rockd_checkin,
    multiple_spot_to_fieldsite,
    spot_to_checkin
)
from .image_utils import sync_checkin_image_to_strabospot
from .strabospot_setup_utils import provision_strabospot_resources
from .sync_to_strabo_pipeline import sync_checkins_to_strabospot
from . import ImageSyncRequest, SyncCheckinsRequest

convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)

@convert_router.post("/image")
async def convert_image(body: ImageSyncRequest) -> Any:
    return await sync_checkin_image_to_strabospot(
        checkin_id=body.checkin_id,
        strabo_token=body.strabo_token,
        rockd_token=body.rockd_token,
        spot_id=body.spot_id,
    )

@convert_router.post("/sync-checkins-to-strabo")
async def sync_checkins_to_strabo(body: SyncCheckinsRequest) -> Any:
    """
    Full pipeline per checkin:
      1. Convert checkin → StraboSpot spot (single Feature format).
      2. POST spot to StraboSpot dataset.
      3. On 200: sync image + save spot_id to Rockd.
    Returns { sentCheckinIds, imageFailedCheckinIds, failedCheckins }.
    """
    return await sync_checkins_to_strabospot(
        checkins=body.checkins,
        strabo_token=body.strabo_token,
        dataset_id=body.dataset_id,
        rockd_token=body.rockd_token,
    )


@convert_router.post("/strabospot-setup")
async def strabospot_setup(
    authorization: str = Header(..., alias="Authorization"),
) -> Any:
    """
    Idempotently provisions a 'Rockd Checkins' dataset and 'Rockd Integration'
    project in StraboSpot, links them, and returns their IDs for the client
    to persist in localStorage.

    Pass the StraboSpot JWT as:  Authorization: Bearer <strabo_access_token>
    """
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be: Bearer <strabo_token>")
    strabo_token = authorization[7:].strip()
    if not strabo_token:
        raise HTTPException(status_code=401, detail="StraboSpot token is missing from Authorization header.")
    return await provision_strabospot_resources(strabo_token)


@convert_router.post("/field-site")
async def convert_field_site(
    payload: Union[dict, List[dict]] = Body(...),
    in_: str = Query(..., alias="in"),
    out: str = Query(..., alias="out"),
    bulk: bool = Query(False, alias="bulk"),
) -> Any:
    match (in_.lower(), out.lower()):
        case ("spot", "fieldsite"):
            return multiple_spot_to_fieldsite(payload)
        case ("checkin", "fieldsite"):
            return multiple_checkin_to_fieldsite(payload)
        case ("fieldsite", "checkin"):
            fss = payload if isinstance(payload, list) else [payload]
            results = multiple_fieldsite_to_rockd_checkin(fss)
            return results[0] if len(results) == 1 else results
        case ("fieldsite", "spot"):
            return fieldsite_to_spot(payload, bulk=bulk)
        case ("checkin", "spot"):
            return checkin_to_spot(payload, bulk=bulk)
        case ("spot", "checkin"):
            return spot_to_checkin(payload, bulk=bulk)
        case _:
            raise HTTPException(
                status_code=400,
                detail="Unsupported conversion. Use in=[spot|fieldsite|checkin], out=[fieldsite|checkin|spot].",
            )