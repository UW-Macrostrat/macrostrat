"""
This file defines all the API route handlers for the Rockd checkins <-> StraboSpot spots conversion.

Endpoints defined here:
  POST /convert/image               Syncs a Rockd photo to StraboSpot
  POST /convert/sync-checkins-to-strabo   Sends a batch of checkins to StraboSpot
  POST /convert/strabospot-setup    Creates the StraboSpot dataset and project
  POST /convert/field-site          Converts data between Rockd and StraboSpot formats
"""

from typing import Any, List, Optional, Union

from fastapi import APIRouter, Body, Header, HTTPException, Query

# Import the request body models defined in __init__.py
from . import ImageSyncRequest, SyncCheckinsRequest

# Import the conversion helper functions from their respective modules
from .convert_utils import (
    checkin_to_spot,
    fieldsite_to_spot,
    multiple_checkin_to_fieldsite,
    multiple_fieldsite_to_rockd_checkin,
    multiple_spot_to_fieldsite,
    spot_to_checkin,
)
from .image_utils import sync_checkin_image_to_strabospot
from .strabospot_setup_utils import provision_strabospot_resources
from .sync_to_strabo_pipeline import sync_checkins_to_strabospot

# Create the router that groups all these endpoints under the /convert prefix
convert_router = APIRouter(
    prefix="/convert",
    tags=["convert"],
    responses={404: {"description": "Not found"}},
)


@convert_router.post("/image")
async def convert_image(body: ImageSyncRequest) -> Any:
    """
    Syncs a single Rockd checkin image over to StraboSpot.

    Steps handled by this endpoint:
      1. Fetch the checkin from Rockd using the checkin ID.
      2. Download the photo from Rockd storage.
      3. Upload the photo to StraboSpot.
      4. Save the StraboSpot spot ID back to the Rockd checkin db table.

    A Rockd token and a StraboSpot token is required for authentication.
    If no spot ID is provided the checkin ID is used as the spot ID.
    """
    return await sync_checkin_image_to_strabospot(
        checkin_id=body.checkin_id,
        strabo_token=body.strabo_token,
        rockd_token=body.rockd_token,
        spot_id=body.spot_id,
    )


@convert_router.post("/sync-checkins-to-strabo")
async def sync_checkins_to_strabo(body: SyncCheckinsRequest) -> Any:
    """
    Sends a batch of Rockd checkins to a StraboSpot dataset all at once.

    For each checkin in the list, this endpoint:
      1. Converts the checkin into the StraboSpot spot format.
      2. Posts the spot to the specified StraboSpot dataset.
      3. If the post succeeds, syncs the photo and saves the spot ID back to Rockd.

    Returns a summary with which checkins succeeded, which had image failures,
    and which failed entirely.
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
    Sets up the StraboSpot account for Rockd integration.

    This endpoint creates a dataset called Rockd Checkins and a project called
    Rockd Integration inside StraboSpot if they do not already exist.
    It then links the dataset to the project.
    Finally it returns the dataset ID and project ID so the client can save them.

    This is safe to call multiple times. If the dataset or project already exists
    it will find and reuse them rather than creating duplicates.

    The caller must pass their StraboSpot token in the Authorization header
    in the format: Bearer your_token_here
    """
    # Make sure the header starts with "Bearer " before extracting the token
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be: Bearer your_strabo_token",
        )

    # Strip off the "Bearer " prefix to get just the raw token string
    strabo_token = authorization[7:].strip()

    if not strabo_token:
        raise HTTPException(
            status_code=401,
            detail="StraboSpot token is missing from Authorization header.",
        )

    return await provision_strabospot_resources(strabo_token)


@convert_router.post("/field-site")
async def convert_field_site(
    payload: Union[dict, List[dict]] = Body(...),
    in_: str = Query(..., alias="in"),
    out: str = Query(..., alias="out"),
    bulk: bool = Query(False, alias="bulk"),
) -> Any:
    """
    A conversion endpoint for switching data between formats.

    The in and out query parameters tell the endpoint what format the data is
    coming from and what format to convert it into.

    Conversions:
      spot to fieldsite     Convert StraboSpot GeoJSON features into FieldSite objects
      checkin to fieldsite  Convert Rockd checkins into FieldSite objects
      fieldsite to checkin  Convert FieldSite objects into Rockd checkin format
      fieldsite to spot     Convert FieldSite objects into StraboSpot GeoJSON features
      checkin to spot       Convert Rockd checkins into StraboSpot spot format
      spot to checkin       Convert StraboSpot spots into Rockd checkin format

    The bulk parameter controls whether to expect a single item or many items.
    When bulk is false the response is a single object.
    When bulk is true the response is a list.
    """
    # Normalize the in and out values to lowercase before matching
    match (in_.lower(), out.lower()):
        case ("spot", "fieldsite"):
            return multiple_spot_to_fieldsite(payload)

        case ("checkin", "fieldsite"):
            return multiple_checkin_to_fieldsite(payload)

        case ("fieldsite", "checkin"):
            # Wrap a single dict in a list so the bulk converter always receives a list
            fss = payload if isinstance(payload, list) else [payload]
            results = multiple_fieldsite_to_rockd_checkin(fss)
            # If only one result came back, unwrap it from the list
            return results[0] if len(results) == 1 else results

        case ("fieldsite", "spot"):
            return fieldsite_to_spot(payload, bulk=bulk)

        case ("checkin", "spot"):
            return checkin_to_spot(payload, bulk=bulk)

        case ("spot", "checkin"):
            return spot_to_checkin(payload, bulk=bulk)

        case _:
            # None of the known combinations matched, so return a helpful error
            raise HTTPException(
                status_code=400,
                detail="Unsupported conversion. Use in=[spot|fieldsite|checkin], out=[fieldsite|checkin|spot].",
            )
