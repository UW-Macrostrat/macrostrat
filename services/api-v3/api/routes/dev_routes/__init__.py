from typing import Any, List, Union

from fastapi import APIRouter, Body, HTTPException, Query

from .convert_utils import (
    checkin_to_spot,
    fieldsite_to_spot,
    multiple_checkin_to_fieldsite,
    multiple_fieldsite_to_rockd_checkin,
    multiple_spot_to_fieldsite,
    spot_to_checkin,
)

convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)

@convert_router.post("/image")


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
