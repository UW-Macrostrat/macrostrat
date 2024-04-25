"""
Look for USGS geologic maps from the Nevada Bureau of Mines and Geology.
"""

import csv
import os.path
import re
import sys

import bs4
import requests
from macrostrat.map_integration import config  # type: ignore[import-untyped]


def is_valid_url(url: str) -> bool:
    """
    Return whether the given URL is one that we are interested in downloading.
    """
    return url.startswith("https://data.nbmg.unr.edu/Public/") and url.endswith(".zip")


def main() -> None:
    """
    Scrape NBMG's website for URLs of interest, and print the resulting objects.
    """
    url_to_scrape = "https://nbmg.unr.edu/USGS.html"
    resp = requests.get(url_to_scrape, timeout=config.TIMEOUT)
    soup = bs4.BeautifulSoup(resp.text, "html.parser")
    links = [x for x in soup.find_all("a") if is_valid_url(x["href"])]

    writer = csv.DictWriter(sys.stdout, ["name", "slug", "url", "website", "s3_prefix"])
    writer.writeheader()

    for link in links:
        filename = link["href"].split("/")[-1]
        (root, _) = os.path.splitext(filename)
        raw_slug = "nbmg_" + re.sub(r"\W", "_", root, flags=re.ASCII)

        writer.writerow(
            {
                "name": link.text,
                "slug": raw_slug.lower(),
                "url": link["href"],
                "website": url_to_scrape,
                "s3_prefix": "nbmg",
            }
        )


if __name__ == "__main__":
    main()
