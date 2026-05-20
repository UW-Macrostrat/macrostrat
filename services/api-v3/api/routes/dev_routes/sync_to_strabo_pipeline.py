"""
sync_to_strabo_pipeline.py

Syncs a batch of Rockd checkins into StraboSpot. Per checkin:
  1. Convert checkin → StraboSpot Feature.
  2. POST Feature to the user's StraboSpot dataset.
  3. On success: upload photo and save spot_id back to Rockd.
"""

import httpx
from fastapi import HTTPException

from .convert_utils import checkin_to_spot
from .image_utils import sync_checkin_image_to_strabospot

STRABOSPOT_DATASET_SINGLE_SPOT_ENDPOINT = (
    "https://strabospot.org/jwtdb/datasetsinglespot"
)


async def sync_checkins_to_strabospot(
    checkins: list[dict],
    strabo_token: str,
    dataset_id: int,
    rockd_token: str,
) -> dict:
    """
    Sync a list of Rockd checkins into a StraboSpot dataset.

    Image failures are tracked separately — a failed photo upload does NOT
    mark the checkin as failed, since the spot was already saved.

    Returns:
        {
            "success":               bool — True only if zero checkins failed.
            "sentCheckinIds":        list — IDs successfully posted.
            "imageFailedCheckinIds": list — IDs where photo upload failed.
            "failedCheckins":        list — { checkinId, message } for hard failures.
        }
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
            # bulk=False produces a bare Feature (not a FeatureCollection),
            # which is what the datasetsinglespot endpoint expects.
            converted = checkin_to_spot(checkin, bulk=False)

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

            try:
                await sync_checkin_image_to_strabospot(
                    checkin_id=checkin_id,
                    strabo_token=strabo_token,
                    rockd_token=rockd_token,
                    spot_id=checkin_id,
                )
            except Exception:
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
