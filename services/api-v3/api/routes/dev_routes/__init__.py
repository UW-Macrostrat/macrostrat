from convert_utils import *
from fastapi import APIRouter

convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)

# _________________________________API ROUTE___________________________________
@convert_router.post("/field-site")
async def convert_field_site(
    payload: Union[dict, List[dict]] = Body(...),
    in_: str = Query(..., alias="in"),
    out: str = Query(..., alias="out"),
    bulk: bool = Query(False, alias="bulk"),
) -> Any:
    key = (in_.lower(), out.lower())
    if key == ("spot", "fieldsite"):
        return multiple_spot_to_fieldsite(payload)
    # output a b
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
        if bulk:
            return checkin_to_spot(payload)
        else:
            return checkin_to_spot_single(payload)
    if key == ("spot", "checkin"):
        if bulk:
            return spot_to_checkin(payload)
        else:
            return spot_to_checkin_single(payload)
    raise HTTPException(
        status_code=400,
        detail="Unsupported conversion. Use in=[spot|fieldsite|checkin], out=[fieldsite|checkin|spot].",
    )