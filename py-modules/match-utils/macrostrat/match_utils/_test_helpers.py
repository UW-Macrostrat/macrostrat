import json
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LITHOLOGIES_URL = "https://dev.macrostrat.org/api/v2/defs/lithologies?all=true"


def _records_from_payload(payload):
    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        return []

    candidates = [
        payload.get("data"),
        payload.get("lithologies"),
    ]

    success = payload.get("success")
    if isinstance(success, dict):
        candidates.extend(
            [
                success.get("data"),
                success.get("lithologies"),
            ]
        )

    for candidate in candidates:
        if isinstance(candidate, list):
            return candidate

    return []


def _name_from_record(record):
    if isinstance(record, str):
        return record

    if not isinstance(record, dict):
        return None

    for key in ("lith", "name", "lithology", "lith_name"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


@lru_cache(maxsize=1)
def get_test_lith_names():
    request = Request(
        LITHOLOGIES_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "macrostrat-pytest",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(
            f"Could not fetch lithologies from {LITHOLOGIES_URL}"
        ) from exc

    records = _records_from_payload(payload)

    lith_names = sorted(
        {
            name.lower()
            for record in records
            if (name := _name_from_record(record)) is not None
        }
    )

    if not lith_names:
        raise RuntimeError(
            f"No lithology names found in response from {LITHOLOGIES_URL}"
        )

    return lith_names
