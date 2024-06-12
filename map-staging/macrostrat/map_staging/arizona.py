"""
Look for geologic maps from the Arizona Geological Survey.
"""

import csv
import json
import re
import sys
from typing import Any

import requests
from requests.adapters import HTTPAdapter

SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=5))
TIMEOUT = 10  # seconds


def collect_metadata() -> list[dict[str, Any]]:
    """
    Return all items in the Arizona Geological Survey Digital Geologic Map collection.
    """
    current_url = "https://data.azgs.arizona.edu/api/v1/metadata?collection_group=ADGM"
    items = []

    while current_url:
        resp = SESSION.get(current_url, timeout=TIMEOUT)
        api_resp = json.loads(resp.text)

        items.extend(api_resp["data"])

        next_urls = [x["href"] for x in api_resp["links"] if x["rel"] == "next"]
        current_url = next_urls[0] if next_urls else None

    return items


def main() -> None:
    """
    Scrape the Arizona Geological Survey and print a CSV file to standard out.

    The CSV file can be processed with `macrostrat maps ingest-from-csv`.
    """
    maps = collect_metadata()

    writer = csv.DictWriter(
        sys.stdout,
        [
            "slug",
            "name",
            "website_url",
            "archive_url",
            "ref_title",
            "ref_authors",
            "ref_year",
        ],
    )
    writer.writeheader()

    for map in maps:
        collection_id = map["collection_id"]
        normalized_id = re.sub(r"\W", "_", collection_id).lower()

        slug = f"arizona_{normalized_id}"
        name = map["metadata"]["title"]

        website_url = None
        ref_title = name
        ref_authors = None
        ref_year = map["metadata"]["year"]

        for link in map["metadata"]["links"]:
            if link["name"] == "UA Library":
                website_url = link["url"]
            if link["name"] == "AZGS old" and not website_url:
                website_url = link["url"]

        for author in map["metadata"]["authors"]:
            if ref_authors:
                ref_authors += f'; {author["person"]}'
            else:
                ref_authors = author["person"]

        for file in map["metadata"]["files"]:
            base_url = f"https://data.azgs.arizona.edu/api/v1/collections/{collection_id}"
            filename = file["name"]
            archive_url = f"{base_url}/{filename}"

            if file["type"].startswith("gisdata:"):

                if filename.endswith(".kmz") or filename == "KMZ.zip":
                    continue

                writer.writerow(
                    {
                        "slug": slug,
                        "name": name,
                        "website_url": website_url,
                        "archive_url": archive_url,
                        "ref_title": ref_title,
                        "ref_authors": ref_authors,
                        "ref_year": ref_year,
                    }
                )


if __name__ == "__main__":
    main()
