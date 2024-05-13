"""
Look for geologic maps from the Alaska Division of Geological & Geophysical Surveys.
"""

import csv
import sys
import urllib.parse

import bs4
import requests

TIMEOUT = 10  # seconds


def add_hostname(hostname: str, url: str) -> str:
    """
    Ensure that the given URL has a scheme and hostname specified.
    """
    parts = urllib.parse.urlparse(url)
    if not parts.scheme:
        parts = parts._replace(scheme="https")
    if not parts.netloc:
        parts = parts._replace(netloc=hostname)
    return parts.geturl()


def get_hrefs(soup: bs4.BeautifulSoup) -> list[str]:
    """
    Return the `href` attributes for all the anchor tags in `soup`.
    """
    urls = []
    for anchor in soup.find_all("a"):
        if url := anchor.get("href", ""):
            urls.append(url)
    return urls


def main() -> None:
    """
    Scrape the Alaska DGGS website and print a CSV file to standard out.

    The CSV file can be processed with `macrostrat maps ingest-from-csv`.
    """
    writer = csv.DictWriter(
        sys.stdout,
        [
            "slug",
            "name",
            "website_url",
            "archive_url",
        ],
    )
    writer.writeheader()

    ## Visit https://dggs.alaska.gov/pubs/ -> Geospatial Data Only = Yes.

    search_url = "https://dggs.alaska.gov/pubs/pubs?title=&author=&pubnumber=&keyword=&keywordWildcard=all&quadrangle=&publisher=All&year=&startyear=&endyear=&digitaldata=Yes&reqtype=Search+Pubs"
    resp = requests.get(search_url, timeout=TIMEOUT)
    soup = bs4.BeautifulSoup(resp.text, "html.parser")

    ## Collect links to individual reports.

    report_urls = [
        add_hostname("dggs.alaska.gov", url)
        for url in get_hrefs(soup)
        if url.startswith("/pubs/id/")
    ]

    ## Scrape each report for links to shapefiles.

    for report_url in report_urls:
        resp = requests.get(report_url, timeout=TIMEOUT)
        soup = bs4.BeautifulSoup(resp.text, "html.parser")

        name = soup.title.text
        slug = "alaska_dggs_" + report_url.split("/")[-1]

        ## Attempt to locate and parse the Geospatial & Analytical Data table.

        for row in soup.find_all("tr"):
            cols = row.find_all("td")

            if len(cols) >= 2 and "Shapefile" in cols[1].text:
                archive_urls = [
                    add_hostname("dggs.alaska.gov", url) for url in get_hrefs(cols[0])
                ]
                for archive_url in archive_urls:
                    writer.writerow(
                        {
                            "slug": slug,
                            "name": name,
                            "website_url": report_url,
                            "archive_url": archive_url,
                        }
                    )


if __name__ == "__main__":
    main()
