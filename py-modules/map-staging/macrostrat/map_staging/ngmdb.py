"""
Look for geologic maps from the National Geologic Map Database.
"""

import csv
import re
import sys
import urllib.parse

import bs4
import requests
from requests.adapters import HTTPAdapter

SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=5))
TIMEOUT = 30  # seconds


def main() -> None:
    """
    Read in a CSV file from the USGS, and print a new CSV file to standard out.

    The CSV file can be processed with `macrostrat maps ingest-from-csv`.
    """
    input_file = sys.argv[1]

    with open(input_file, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
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

        for row in reader:
            if row["gis_data"].lower() == "yes":
                website_url = row["url"]
                resp = SESSION.get(website_url, timeout=TIMEOUT)
                soup = bs4.BeautifulSoup(resp.text, "html.parser")

                slug = "ngmdb_" + row["publication_id"]
                name = None
                archive_url = None

                for span in soup.find_all("span"):
                    if span.text.startswith("Title:"):
                        if match := re.match(r"(\s*)Title:(.*)", span.text):
                            name = match.group(2).strip()

                for anchor in soup.find_all("a"):
                    if anchor.text.startswith("Shapefile version"):
                        parts = urllib.parse.urlparse(anchor["href"])
                        if parts.scheme:
                            archive_url = anchor["href"]
                        else:
                            parts = urllib.parse.urlparse(website_url)
                            archive_url = parts._replace(path=anchor["href"]).geturl()

                if name and archive_url:
                    writer.writerow(
                        {
                            "slug": slug,
                            "name": name,
                            "website_url": website_url,
                            "archive_url": archive_url,
                            "ref_title": row["title"],
                            "ref_authors": row["authors"],
                            "ref_year": row["year"],
                        }
                    )


if __name__ == "__main__":
    main()
