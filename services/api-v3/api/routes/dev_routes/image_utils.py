from typing import Optional
from datetime import datetime, timezone
import httpx
import os
from fastapi import HTTPException

#__________GLOBALS________________________________
STRABOSPOT_IMAGE_ENDPOINT = "https://strabospot.org/jwtdb/image"


async def sync_checkin_image_to_strabospot(
    checkin_id: int,
    strabo_token: str,
    rockd_token: str,
    spot_id: Optional[int] = None,
) -> dict:
    """
    1. Fetches the Rockd checkin.
    2. Pulls the Rockd image blob.
    3. Uploads the image to StraboSpot.
    4. Saves spot_id back to the Rockd checkin.
    spot_id defaults to checkin_id if not provided.
    """
    spot_id = spot_id if spot_id is not None else checkin_id
    checkin = await _fetch_rockd_checkin(checkin_id, rockd_token)
    person_id, photo_id = checkin.get("person_id"), checkin.get("photo")

    if person_id is None:
        raise HTTPException(status_code=400, detail=f"Checkin {checkin_id} does not have person_id.")

    save_result = await _save_rockd_checkin_spot_id(checkin_id, spot_id, rockd_token)

    if photo_id is None:
        return {
            "success": True, "checkin_id": checkin_id, "spot_id": spot_id,
            "photo_uploaded": False, "message": "Checkin has no photo. Saved spot_id only.",
            "rockd_checkin_spot_result": save_result,
        }

    person_id, photo_id = int(person_id), int(photo_id)
    image_bytes, content_type = await _fetch_rockd_photo_bytes(person_id, photo_id, rockd_token)
    strabo_upload_result = await _upload_photo_to_strabospot(strabo_token, photo_id, image_bytes, content_type)

    return {
        "success": True, "checkin_id": checkin_id, "spot_id": spot_id,
        "person_id": person_id, "photo_id": photo_id, "photo_uploaded": True,
        "strabospot_image_result": strabo_upload_result,
        "rockd_checkin_spot_result": save_result,
    }


#________________IMAGE HELPERS_________________________

def _get_rockd_api_url() -> str:
    url = os.getenv("ROCKD_API_URL") or os.getenv("ROCKD_API_BASE_URL")
    if url is None:
        raise HTTPException(status_code=500, detail="Missing ROCKD_API_URL environment variable.")
    return url.rstrip("/")

async def _fetch_rockd_checkin(checkin_id: int, rockd_token: str) -> dict:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        res = await client.get(
            f"{_get_rockd_api_url()}/protected/checkins",
            params={"checkin_id": checkin_id},
            headers={"Accept": "*/*", "Authorization": f"Bearer {rockd_token}"},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=f"Failed to fetch Rockd checkin {checkin_id}: {res.text}")
    data = res.json().get("success", {}).get("data")
    if isinstance(data, list):
        if not data:
            raise HTTPException(status_code=404, detail=f"No Rockd checkin found for checkin_id={checkin_id}.")
        return data[0]
    if isinstance(data, dict):
        return data
    raise HTTPException(status_code=502, detail=f"Unexpected Rockd checkin response for checkin_id={checkin_id}.")


async def _fetch_rockd_photo_bytes(person_id: int, photo_id: int, rockd_token: str) -> tuple[bytes, str]:
    """
    Rockd returns a 307 redirect to a pre-signed S3 URL.
    We must NOT forward the Authorization header to S3, or it will reject the request.
    So we follow the redirect manually in two steps.
    """
    rockd_url = f"{_get_rockd_api_url()}/protected/image/{person_id}/banner/{photo_id}"

    # Step 1: hit Rockd to get the pre-signed S3 redirect URL
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
            res = await client.get(
                rockd_url,
                headers={"Accept": "*/*", "Authorization": f"Bearer {rockd_token}"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Timed out contacting Rockd at {rockd_url}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error contacting Rockd: {e}")

    if res.status_code not in (301, 302, 307, 308):
        if res.status_code >= 400:
            raise HTTPException(status_code=res.status_code, detail=f"Rockd returned error for photo {photo_id}: {res.text}")
        # Unexpected non-redirect: treat body as the image directly
        return res.content, res.headers.get("content-type") or "image/jpeg"

    s3_url = res.headers.get("location")
    if not s3_url:
        raise HTTPException(status_code=502, detail=f"Rockd returned {res.status_code} but no Location header for photo {photo_id}")

    # Step 2: fetch the image from S3 WITHOUT the Authorization header
    # (S3 pre-signed URLs reject requests that also carry an Authorization header)
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
            s3_res = await client.get(s3_url, headers={"Accept": "*/*"})
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Timed out downloading image from S3 (redirected from Rockd photo {photo_id}). S3 URL: {s3_url}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network error downloading from S3: {e}")

    if s3_res.status_code >= 400:
        raise HTTPException(
            status_code=s3_res.status_code,
            detail=f"S3 returned error for photo {photo_id} (status {s3_res.status_code}). URL: {s3_url[:120]}..."
        )

    return s3_res.content, s3_res.headers.get("content-type") or "image/jpeg"


async def _upload_photo_to_strabospot(strabo_token: str, photo_id: int, image_bytes: bytes, content_type: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            STRABOSPOT_IMAGE_ENDPOINT,
            headers={"Accept": "*/*", "Authorization": f"Bearer {strabo_token}"},
            data={"id": str(photo_id), "modified_timestamp": str(int(datetime.now(timezone.utc).timestamp()))},
            files={"image_file": (f"{photo_id}.jpg", image_bytes, content_type)},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=f"Failed to upload photo {photo_id} to StraboSpot: {res.text}")
    try: return res.json()
    except Exception: return {"status": res.status_code, "body": res.text}


async def _save_rockd_checkin_spot_id(checkin_id: int, spot_id: int, rockd_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{_get_rockd_api_url()}/protected/checkin-spot",
            headers={"Content-Type": "application/json"},
            json={"checkin_id": checkin_id, "spot_id": spot_id, "token": rockd_token},
        )
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=f"Image upload may have succeeded, but failed to save spot_id for checkin_id={checkin_id}: {res.text}")
    try: return res.json()
    except Exception: return {"status": res.status_code, "body": res.text}
