from typing import Any
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException


#____________GLOBALS__________________


STRABOSPOT_MY_DATASETS_ENDPOINT = "https://strabospot.org/jwtdb/myDatasets"
STRABOSPOT_MY_PROJECTS_ENDPOINT = "https://strabospot.org/jwtdb/myProjects"
STRABOSPOT_CREATE_DATASET_ENDPOINT = "https://strabospot.org/jwtdb/dataset"
STRABOSPOT_CREATE_PROJECT_ENDPOINT = "https://strabospot.org/jwtdb/project"

#_____________STRABOSPOT-SETUP LOGIC_________________________
"""
    Fetches existing datasets → finds or creates "Rockd Checkins" dataset.
    Fetches existing projects → finds or creates "Rockd Integration" project.
    Links the dataset to the project (if not already done).
    Returns all IDs back to the client so the client can save these in localStorage.
"""

async def provision_strabospot_resources(strabo_token: str) -> dict:
    """
    Idempotently ensures a 'Rockd Checkins' dataset and 'Rockd Integration'
    project exist in StraboSpot, linked together.
    Returns {"dataset_id": int, "project_id": int}.
    """
    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    today_mdy = now.strftime("%m/%d/%Y")
    today_ymd = now.strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ── Datasets ──────────────────────────────────────────────────────────
        datasets_body = await _strabo_get(client, STRABOSPOT_MY_DATASETS_ENDPOINT, strabo_token)
        datasets: list[dict] = datasets_body.get("datasets") or []
        dataset = next((d for d in datasets if d.get("name") == "Rockd Checkins"), None)

        if dataset is None:
            existing_ids = [int(d["id"]) for d in datasets if d.get("id") is not None]
            dataset_id = _unique_numeric_id(existing_ids)
            dataset = await _strabo_post(client, STRABOSPOT_CREATE_DATASET_ENDPOINT, strabo_token, {
                "id": dataset_id,
                "name": "Rockd Checkins",
                "modified_timestamp": now_ts,
                "date": today_mdy,
            })

        dataset_id = int(dataset["id"])

        # ── Projects ──────────────────────────────────────────────────────────
        projects_body = await _strabo_get(client, STRABOSPOT_MY_PROJECTS_ENDPOINT, strabo_token)
        projects: list[dict] = projects_body.get("projects") or []
        project = next((p for p in projects if p.get("name") == "Rockd Integration"), None)

        if project is None:
            existing_ids = [int(p["id"]) for p in projects if p.get("id") is not None]
            project_id = _unique_numeric_id(existing_ids)
            project = await _strabo_post(client, STRABOSPOT_CREATE_PROJECT_ENDPOINT, strabo_token, {
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
                    "orientation": False, "_3dstructures": False, "images": False,
                    "sample": False, "inferences": False, "nesting": False,
                    "right_hand_rule": False, "drop_down_to_finish": False, "student_mode": False,
                },
                "reports": None,
            })

        project_id = int(project["id"])

        # ── Link dataset → project (idempotent — StraboSpot ignores duplicates) ─
        await _strabo_post(
            client,
            f"https://strabospot.org/jwtdb/projectDatasets/{project_id}",
            strabo_token,
            {"id": dataset_id},
        )

    return {"dataset_id": dataset_id, "project_id": project_id}


#_____________________STRABO SETUP HELPERS________________________________


def _strabo_headers(token: str) -> dict:
    return {"Accept": "*/*", "Authorization": f"Bearer {token}"}


async def _strabo_get(client: httpx.AsyncClient, url: str, token: str) -> Any:
    res = await client.get(url, headers=_strabo_headers(token))
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=f"StraboSpot GET {url} failed: {res.text}")
    return res.json()


async def _strabo_post(client: httpx.AsyncClient, url: str, token: str, payload: dict) -> Any:
    res = await client.post(
        url,
        headers={**_strabo_headers(token), "Content-Type": "application/json"},
        json=payload,
    )
    if res.status_code >= 400:
        raise HTTPException(status_code=res.status_code, detail=f"StraboSpot POST {url} failed: {res.text}")
    return res.json()


def _unique_numeric_id(existing_ids: list[int]) -> int:
    import random
    candidate = int(f"{int(datetime.now(timezone.utc).timestamp())}{random.randint(1000, 9999)}")
    while candidate in existing_ids:
        candidate = int(f"{int(datetime.now(timezone.utc).timestamp())}{random.randint(1000, 9999)}")
    return candidate


