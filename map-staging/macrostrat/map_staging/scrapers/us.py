"""
Look for USGS geologic maps from the National Geologic Map Database.
"""

import csv
import re
import sys
import urllib.parse

import bs4
import requests
from macrostrat.map_integration import config  # type: ignore[import-untyped]


def main() -> None:
    """
    Read in a CSV file from the USGS, and print any resulting objects.
    """
    input_file = sys.argv[1]

    with open(input_file, mode="r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        writer = csv.DictWriter(
            sys.stdout,
            [
                "name",
                "slug",
                "url",
                "website",
                "s3_prefix",
                "ref_title",
                "ref_authors",
                "ref_year",
            ],
        )
        writer.writeheader()

        for row in reader:
            if row["gis_data"] == "yes":
                url_to_scrape = row["url"]
                resp = requests.get(url_to_scrape, timeout=config.TIMEOUT)
                soup = bs4.BeautifulSoup(resp.text, "html.parser")

                title = None
                url = None
                raw_slug = "ngmdb_" + row["publication_id"]

                for span in soup.find_all("span"):
                    if span.text.startswith("Title:"):
                        if match := re.match(r"(\s*)Title:(.*)", span.text):
                            title = match.group(2).strip()

                for link in soup.find_all("a"):
                    if link.text.startswith("Shapefile version"):
                        parsed_url = urllib.parse.urlparse(link["href"])
                        if parsed_url.scheme:
                            url = link["href"]
                        else:
                            parsed_url = urllib.parse.urlparse(url_to_scrape)
                            parsed_url = parsed_url._replace(path=link["href"])
                            url = parsed_url.geturl()

                if title and url:
                    writer.writerow(
                        {
                            "name": title,
                            "slug": raw_slug.lower(),
                            "url": url,
                            "website": url_to_scrape,
                            "s3_prefix": "ngmdb",
                            "ref_title": row["title"],
                            "ref_authors": row["authors"],
                            "ref_year": row["year"],
                        }
                    )


if __name__ == "__main__":
    main()
