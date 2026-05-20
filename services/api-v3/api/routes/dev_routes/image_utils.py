"""
This file handles everything related to syncing a photo from Rockd to StraboSpot.

The main function sync_checkin_image_to_strabospot does four things in order:
  1. Fetches the checkin record from Rockd to find out the person ID and photo ID.
  2. Downloads the photo from Rockd storage.
  3. Uploads the photo to StraboSpot.
  4. Saves the StraboSpot spot ID back to the Rockd checkin record.

The photo download is a two step process because Rockd redirects to a pre-signed
S3 URL. The Authorization header must not be forwarded to S3 or the request fails.
"""

import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import HTTPException

# The StraboSpot endpoint that accepts image uploads
STRABOSPOT_IMAGE_ENDPOINT = "https://strabospot.org/jwtdb/image"


async def sync_checkin_image_to_strabospot(
    checkin_id: int,
    strabo_token: str,
    rockd_token: str,
    spot_id: Optional[int] = None,
) -> dict:
    """
    Runs the full image sync pipeline for one Rockd checkin.

    Steps:
      1. Fetch the checkin from Rockd to get the person ID and photo ID.
      2. Save the spot ID to the Rockd checkin record.
      3. If there is no photo, return early with a success message.
      4. Download the photo from Rockd storage.
      5. Upload the photo to StraboSpot.
      6. Return a result summary.

    The spot ID defaults to the checkin ID if not provided.
    The person ID is needed to build the correct Rockd photo URL.
    """
    # Default the spot ID to the checkin ID if the caller did not specify one
    spot_id = spot_id if spot_id is not None else checkin_id

    checkin = await _fetch_rockd_checkin(checkin_id, rockd_token)
    person_id, photo_id = checkin.get("person_id"), checkin.get("photo")

    if person_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"Checkin {checkin_id} does not have person_id.",
        )

    # Save the spot ID link to Rockd before dealing with the photo
    save_result = await _save_rockd_checkin_spot_id(checkin_id, spot_id, rockd_token)

    # If there is no photo attached, stop here and return success
    if photo_id is None:
        return {
            "success": True,
            "checkin_id": checkin_id,
            "spot_id": spot_id,
            "photo_uploaded": False,
            "message": "Checkin has no photo. Saved spot_id only.",
            "rockd_checkin_spot_result": save_result,
        }

    # Convert both IDs to integers before using them in URLs
    person_id, photo_id = int(person_id), int(photo_id)

    image_bytes, content_type = await _fetch_rockd_photo_bytes(
        person_id, photo_id, rockd_token
    )
    strabo_upload_result = await _upload_photo_to_strabospot(
        strabo_token, photo_id, image_bytes, content_type
    )

    return {
        "success": True,
        "checkin_id": checkin_id,
        "spot_id": spot_id,
        "person_id": person_id,
        "photo_id": photo_id,
        "photo_uploaded": True,
        "strabospot_image_result": strabo_upload_result,
        "rockd_checkin_spot_result": save_result,
    }


# ── Image helper functions ────────────────────────────────────────────────────


def _get_rockd_api_url() -> str:
    """
    Reads the Rockd API base URL from the environment variables.
    Checks for two possible variable names and raises a clear error if neither is set.
    The trailing slash is removed so URLs built from this string do not have double slashes.
    """
    url = os.getenv("ROCKD_API_URL") or os.getenv("ROCKD_API_BASE_URL")
    if url is None:
        raise HTTPException(
            status_code=500,
            detail="Missing ROCKD_API_URL environment variable.",
        )
    return url.rstrip("/")


async def _fetch_rockd_checkin(checkin_id: int, rockd_token: str) -> dict:
    """
    Fetches a single checkin record from the Rockd API by its ID.

    Returns the checkin as a plain dictionary.
    The response from Rockd wraps the data inside a success.data field,
    which can be either a list with one item or a single dictionary.
    Both shapes are handled here.
    Raises an HTTPException if the checkin is not found or the request fails.
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        res = await client.get(
            f"{_get_rockd_api_url()}/protected/checkins",
            params={"checkin_id": checkin_id},
            headers={"Accept": "*/*", "Authorization": f"Bearer {rockd_token}"},
        )

    if res.status_code >= 400:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"Failed to fetch Rockd checkin {checkin_id}: {res.text}",
        )

    # Navigate into the nested response structure to get the actual checkin data
    data = res.json().get("success", {}).get("data")

    if isinstance(data, list):
        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"No Rockd checkin found for checkin_id={checkin_id}.",
            )
        return data[0]

    if isinstance(data, dict):
        return data

    raise HTTPException(
        status_code=502,
        detail=f"Unexpected Rockd checkin response for checkin_id={checkin_id}.",
    )


async def _fetch_rockd_photo_bytes(
    person_id: int, photo_id: int, rockd_token: str
) -> tuple[bytes, str]:
    """
    Downloads a photo from Rockd storage and returns the raw image bytes.

    Rockd does not serve photos directly. Instead it responds with a 307 redirect
    to a temporary pre-signed URL on S3 cloud storage.

    This function handles that two step flow manually:
      Step 1: Ask Rockd for the photo URL. It will respond with a redirect.
      Step 2: Follow the redirect to S3 to download the actual image bytes.

    The Authorization header is intentionally not forwarded to S3 because
    S3 pre-signed URLs already contain the authentication in the URL itself.
    Sending an Authorization header on top of that causes S3 to reject the request.

    Returns a tuple of (image bytes, content type string like image/jpeg).
    """
    rockd_url = f"{_get_rockd_api_url()}/protected/image/{person_id}/banner/{photo_id}"

    # Step 1: ask Rockd for the photo, expecting a redirect response
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
            res = await client.get(
                rockd_url,
                headers={"Accept": "*/*", "Authorization": f"Bearer {rockd_token}"},
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timed out contacting Rockd at {rockd_url}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"Network error contacting Rockd: {e}"
        )

    # Handle unexpected non-redirect responses
    if res.status_code not in (301, 302, 307, 308):
        if res.status_code >= 400:
            raise HTTPException(
                status_code=res.status_code,
                detail=f"Rockd returned error for photo {photo_id}: {res.text}",
            )
        # If for some reason Rockd returned the image directly, use it as-is
        return res.content, res.headers.get("content-type") or "image/jpeg"

    # Extract the S3 URL from the Location header in the redirect response
    s3_url = res.headers.get("location")
    if not s3_url:
        raise HTTPException(
            status_code=502,
            detail=f"Rockd returned {res.status_code} but no Location header for photo {photo_id}",
        )

    # Step 2: fetch the actual image from S3 without an Authorization header
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
            s3_res = await client.get(s3_url, headers={"Accept": "*/*"})
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail=f"Timed out downloading image from S3 (redirected from Rockd photo {photo_id}). S3 URL: {s3_url}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"Network error downloading from S3: {e}"
        )

    if s3_res.status_code >= 400:
        raise HTTPException(
            status_code=s3_res.status_code,
            detail=f"S3 returned error for photo {photo_id} (status {s3_res.status_code}). URL: {s3_url[:120]}...",
        )

    return s3_res.content, s3_res.headers.get("content-type") or "image/jpeg"


async def _upload_photo_to_strabospot(
    strabo_token: str, photo_id: int, image_bytes: bytes, content_type: str
) -> dict:
    """
    Uploads an image file to the StraboSpot image endpoint.

    The image is sent as a multipart form upload which is the format StraboSpot expects.
    The form includes the photo ID, a timestamp, and the image file itself.
    Returns the JSON response from StraboSpot, or a status dict if the response is not JSON.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            STRABOSPOT_IMAGE_ENDPOINT,
            headers={"Accept": "*/*", "Authorization": f"Bearer {strabo_token}"},
            # Form fields that StraboSpot requires alongside the image file
            data={
                "id": str(photo_id),
                "modified_timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            },
            # The image file itself, named with the photo ID and a jpg extension
            files={"image_file": (f"{photo_id}.jpg", image_bytes, content_type)},
        )

    if res.status_code >= 400:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"Failed to upload photo {photo_id} to StraboSpot: {res.text}",
        )

    try:
        return res.json()
    except Exception:
        # If the response is not valid JSON, return the raw status and text
        return {"status": res.status_code, "body": res.text}


async def _save_rockd_checkin_spot_id(
    checkin_id: int, spot_id: int, rockd_token: str
) -> dict:
    """
    Saves a StraboSpot spot ID back to the corresponding Rockd checkin record.

    This creates a permanent link between the Rockd checkin and its StraboSpot spot.
    After this call, the Rockd database knows which spot ID this checkin corresponds to,
    and the checkin will no longer appear as unsynced in the UI.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.post(
            f"{_get_rockd_api_url()}/protected/checkin-spot",
            headers={"Content-Type": "application/json"},
            json={
                "checkin_id": checkin_id,
                "spot_id": spot_id,
                "token": rockd_token,
            },
        )

    if res.status_code >= 400:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"Image upload may have succeeded, but failed to save spot_id for checkin_id={checkin_id}: {res.text}",
        )

    try:
        return res.json()
    except Exception:
        return {"status": res.status_code, "body": res.text}
