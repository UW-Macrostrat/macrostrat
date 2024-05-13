"""
Look for geologic maps from the Nevada Bureau of Mines and Geology.
"""

import csv
import sys

import bs4
import requests
from requests.adapters import HTTPAdapter

SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=5))
TIMEOUT = 30  # seconds


def main() -> None:
    """
    Scrape the NBMG website and print a CSV file to standard out.

    The CSV file can be processed with `macrostrat maps ingest-from-csv`.
    """
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
            "ref_isbn_or_doi",
        ],
    )
    writer.writeheader()

    search_url = "https://nbmg.unr.edu/USGS.html"
    resp = SESSION.get(search_url, timeout=TIMEOUT)
    soup = bs4.BeautifulSoup(resp.text, "html.parser")

    ## Attempt to locate and parse the table of maps.

    for row in soup.find_all("tr"):
        cols = row.find_all("td")

        if len(cols) >= 2:
            for anchor in cols[1].find_all("a"):
                url = anchor.get("href", "")

                if url.startswith("https://data.nbmg.unr.edu/Public/") and url.endswith(".zip"):

                    ## Make an educated guess for the DOI.

                    report_id = cols[0].text.strip()
                    slug_suffix = report_id.replace("-", "_")
                    doi_key = report_id.replace("-", "")
                    website_url = f"https://doi.org/10.3133/{doi_key}"

                    slug = f"nevada_nbmg_{slug_suffix}".lower()
                    name = anchor.text.strip()
                    archive_url = url
                    title = None
                    authors = None
                    year = None
                    doi = f"10.3133/{doi_key}"

                    ## A valid DOI points to the NGMDB.

                    resp = SESSION.get(website_url, timeout=TIMEOUT)
                    soup = bs4.BeautifulSoup(resp.text, "html.parser")

                    if resp.ok:
                        for meta in soup.find_all("meta"):
                            if meta.get("name") == "title":
                                title = meta.get("content")
                                name = title
                            if meta.get("name") == "citation_date":
                                year = meta.get("content")
                            if meta.get("name") == "citation_author":
                                if authors:
                                    authors += "; " + meta.get("content")
                                else:
                                    authors = meta.get("content")
                    else:
                        website_url = search_url  # fallback for when the DOI doesn't pan out

                    writer.writerow(
                        {
                            "slug": slug,
                            "name": name,
                            "website_url": website_url,
                            "archive_url": archive_url,
                            "ref_title": title,
                            "ref_authors": authors,
                            "ref_year": year,
                            "ref_isbn_or_doi": doi,
                        }
                    )


if __name__ == "__main__":
    main()
