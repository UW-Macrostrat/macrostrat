from typing import Any, List, Optional, Union

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from .convert_utils import (
    checkin_to_spot,
    fieldsite_to_spot,
    multiple_checkin_to_fieldsite,
    multiple_fieldsite_to_rockd_checkin,
    multiple_spot_to_fieldsite,
    spot_to_checkin,
    sync_checkin_image_to_strabospot,
)

convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)


class ImageSyncRequest(BaseModel):
    checkin_id: int
    strabo_token: str
    rockd_token: str
    spot_id: Optional[int] = None


@convert_router.post("/image")
async def convert_image(body: ImageSyncRequest) -> Any:
    return await sync_checkin_image_to_strabospot(
        checkin_id=body.checkin_id,
        strabo_token=body.strabo_token,
        rockd_token=body.rockd_token,
        spot_id=body.spot_id,
    )


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