"""
This file handles setting up the StraboSpot account for Rockd integration.

When a user links their StraboSpot account, this code runs to make sure they have:
  A dataset called Rockd Checkins  where synced checkins will be stored as spots
  A project called Rockd Integration  which organizes and owns that dataset

If either the dataset or project already exists it will be reused, not duplicated.
At the end the dataset is linked to the project inside StraboSpot.
The IDs for both are returned to the client to be saved in localStorage.
"""

from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException

# StraboSpot API endpoints for reading and creating datasets and projects
STRABOSPOT_MY_DATASETS_ENDPOINT = "https://strabospot.org/jwtdb/myDatasets"
STRABOSPOT_MY_PROJECTS_ENDPOINT = "https://strabospot.org/jwtdb/myProjects"
STRABOSPOT_CREATE_DATASET_ENDPOINT = "https://strabospot.org/jwtdb/dataset"
STRABOSPOT_CREATE_PROJECT_ENDPOINT = "https://strabospot.org/jwtdb/project"


async def provision_strabospot_resources(strabo_token: str) -> dict:
    """
    Idempotently sets up the required StraboSpot dataset and project for Rockd integration.

    Idempotently means it is safe to call this multiple times.
    If the dataset or project already exists, it finds and reuses them.
    Only creates what is missing.

    Steps:
      1. Fetch the users existing datasets. Find or create Rockd Checkins.
      2. Fetch the users existing projects. Find or create Rockd Integration.
      3. Link the dataset to the project inside StraboSpot.
      4. Return both IDs to the caller.

    Returns a dict with dataset_id and project_id.
    """
    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    # StraboSpot uses month/day/year format for dataset dates
    today_mdy = now.strftime("%m/%d/%Y")
    # ISO format is used for project start dates
    today_ymd = now.strftime("%Y-%m-%d")

    # Reuse a single HTTP client for all requests in this function
    async with httpx.AsyncClient(timeout=30.0) as client:

        # Step 1: find or create the Rockd Checkins dataset
        datasets_body = await _strabo_get(
            client, STRABOSPOT_MY_DATASETS_ENDPOINT, strabo_token
        )
        datasets: list[dict] = datasets_body.get("datasets") or []

        # Look for an existing dataset with the right name
        dataset = next((d for d in datasets if d.get("name") == "Rockd Checkins"), None)

        if dataset is None:
            # Generate a unique ID that does not clash with any existing dataset IDs
            existing_ids = [int(d["id"]) for d in datasets if d.get("id") is not None]
            dataset_id = _unique_numeric_id(existing_ids)

            dataset = await _strabo_post(
                client,
                STRABOSPOT_CREATE_DATASET_ENDPOINT,
                strabo_token,
                {
                    "id": dataset_id,
                    "name": "Rockd Checkins",
                    "modified_timestamp": now_ts,
                    "date": today_mdy,
                },
            )

        dataset_id = int(dataset["id"])

        # Step 2: find or create the Rockd Integration project
        projects_body = await _strabo_get(
            client, STRABOSPOT_MY_PROJECTS_ENDPOINT, strabo_token
        )
        projects: list[dict] = projects_body.get("projects") or []

        # Look for an existing project with the right name
        project = next(
            (p for p in projects if p.get("name") == "Rockd Integration"), None
        )

        if project is None:
            # Generate a unique ID that does not clash with any existing project IDs
            existing_ids = [int(p["id"]) for p in projects if p.get("id") is not None]
            project_id = _unique_numeric_id(existing_ids)

            project = await _strabo_post(
                client,
                STRABOSPOT_CREATE_PROJECT_ENDPOINT,
                strabo_token,
                {
                    "id": project_id,
                    "description": {
                        "project_name": "Rockd Integration",
                        "start_date": today_ymd,
                        "end_date": "",
                        "purpose_of_study": "Syncing Rockd checkins as a spot",
                        "other_team_members": "",
                        "area_of_interest": "",
                        "spot_prefix": "TST",
                        "starting_number_for_spot": "1",
                        "sample_prefix": "S",
                        "instruments": "",
                        "gps_datum": "WGS84",
                        "magnetic_declination": "",
                        "Notes": "Created via Rockd integration",
                    },
                    "daily_setup": {},
                    "rock_units": [],
                    "preferences": {
                        "orientation": False,
                        "_3dstructures": False,
                        "images": False,
                        "sample": False,
                        "inferences": False,
                        "nesting": False,
                        "right_hand_rule": False,
                        "drop_down_to_finish": False,
                        "student_mode": False,
                    },
                    "reports": None,
                },
            )

        project_id = int(project["id"])

        # Step 3: link the dataset to the project
        # StraboSpot ignores this call if the link already exists so it is safe to repeat
        await _strabo_post(
            client,
            f"https://strabospot.org/jwtdb/projectDatasets/{project_id}",
            strabo_token,
            {"id": dataset_id},
        )

    return {"dataset_id": dataset_id, "project_id": project_id}


# ── StraboSpot request helpers ────────────────────────────────────────────────


def _strabo_headers(token: str) -> dict:
    """
    Builds the standard headers needed for authenticated StraboSpot API calls.
    The token is placed in the Authorization header in Bearer format.
    """
    return {"Accept": "*/*", "Authorization": f"Bearer {token}"}


async def _strabo_get(client: httpx.AsyncClient, url: str, token: str) -> Any:
    """
    Sends a GET request to a StraboSpot endpoint with authentication.
    Raises an HTTPException with the StraboSpot error text if the request fails.
    Returns the parsed JSON response on success.
    """
    res = await client.get(url, headers=_strabo_headers(token))
    if res.status_code >= 400:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"StraboSpot GET {url} failed: {res.text}",
        )
    return res.json()


async def _strabo_post(
    client: httpx.AsyncClient, url: str, token: str, payload: dict
) -> Any:
    """
    Sends a POST request to a StraboSpot endpoint with authentication and a JSON body.
    Raises an HTTPException with the StraboSpot error text if the request fails.
    Returns the parsed JSON response on success.
    """
    res = await client.post(
        url,
        # Merge the auth headers with the Content-Type header for JSON
        headers={**_strabo_headers(token), "Content-Type": "application/json"},
        json=payload,
    )
    if res.status_code >= 400:
        raise HTTPException(
            status_code=res.status_code,
            detail=f"StraboSpot POST {url} failed: {res.text}",
        )
    return res.json()


def _unique_numeric_id(existing_ids: list[int]) -> int:
    """
    Generates a numeric ID that does not already exist in the provided list.

    The ID is built from the current Unix timestamp combined with a random four digit number.
    If the candidate happens to collide with an existing ID, it keeps trying new candidates
    until it finds one that is free.
    """
    import random

    candidate = int(
        f"{int(datetime.now(timezone.utc).timestamp())}{random.randint(1000, 9999)}"
    )

    # Keep generating until we find an ID that is not already taken
    while candidate in existing_ids:
        candidate = int(
            f"{int(datetime.now(timezone.utc).timestamp())}{random.randint(1000, 9999)}"
        )

    return candidate
