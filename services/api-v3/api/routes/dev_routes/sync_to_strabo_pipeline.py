import httpx
from fastapi import HTTPException
from .convert_utils import checkin_to_spot
from .image_utils import sync_checkin_image_to_strabospot

STRABOSPOT_DATASET_SINGLE_SPOT_ENDPOINT = "https://strabospot.org/jwtdb/datasetsinglespot"

#_____________SYNC TO STRABO HIGH LEVEL WORKFLOW________________
async def sync_checkins_to_strabospot(
    checkins: list[dict],
    strabo_token: str,
    dataset_id: int,
    rockd_token: str,
) -> dict:
    """
    For each checkin:
      1. Convert checkin → StraboSpot bare Feature (bulk=False format).
      2. POST spot to StraboSpot dataset.
      3. If 200, sync image + save spot_id to Rockd via sync_checkin_image_to_strabospot.
    Returns { sentCheckinIds, imageFailedCheckinIds, failedCheckins }.
    """
    successes: list[int] = []
    image_failed_ids: list[int] = []
    failed_checkins: list[dict] = []

    for checkin in checkins:
        checkin_id = checkin.get("checkin_id") or checkin.get("id")
        if checkin_id is None:
            failed_checkins.append({"checkinId": -1, "message": "Missing checkin_id."})
            continue
        checkin_id = int(checkin_id)

        try:
            # Step A: convert checkin → bare StraboSpot Feature
            converted = checkin_to_spot(checkin, bulk=False)

            # Step B: POST spot to StraboSpot dataset
            async with httpx.AsyncClient(timeout=30.0) as client:
                post_res = await client.post(
                    f"{STRABOSPOT_DATASET_SINGLE_SPOT_ENDPOINT}/{dataset_id}",
                    headers={
                        "Accept": "*/*",
                        "Authorization": f"Bearer {strabo_token}",
                        "Content-Type": "application/json",
                    },
                    json=converted,
                )

            if post_res.status_code != 200:
                raise HTTPException(
                    status_code=post_res.status_code,
                    detail=f"StraboSpot rejected spot for checkin {checkin_id}: {post_res.text}",
                )

            # Step C: image sync + save spot_id to Rockd
            try:
                await sync_checkin_image_to_strabospot(
                    checkin_id=checkin_id,
                    strabo_token=strabo_token,
                    rockd_token=rockd_token,
                    spot_id=checkin_id,
                )
            except Exception as img_err:
                image_failed_ids.append(checkin_id)

            successes.append(checkin_id)

        except HTTPException as e:
            failed_checkins.append({"checkinId": checkin_id, "message": e.detail})
        except Exception as e:
            failed_checkins.append({"checkinId": checkin_id, "message": str(e)})

    return {
        "success": len(failed_checkins) == 0,
        "sentCheckinIds": successes,
        "imageFailedCheckinIds": image_failed_ids,
        "failedCheckins": failed_checkins,
    }