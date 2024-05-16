"""
Process maps from the CriticalMAAS Month 09 spreadsheet.
"""

import csv
import re
import sys

import bs4
import requests

TIMEOUT = 10  # seconds


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
                "ref_source",
            ],
        )
        writer.writeheader()

        for row in reader:
            if re.match(r"^[0-9A-Fa-f]{64}", row["COG ID"]):
                website_url = row.get("NGMDB Product Link", "")
                archive_url = (
                    "https://s3.amazonaws.com/public.cdr.land/results/" + row["COG ID"] + ".zip"
                )
                authors = None
                year = None
                source = None

                if website_url.startswith("http"):
                    slug = "criticalmaas_09_ngmdb_" + row["NGMDB ProdID"]
                    name = f'TA1 NGMDB {row["NGMDB ProdID"]}'

                    resp = requests.get(website_url, timeout=TIMEOUT)
                    soup = bs4.BeautifulSoup(resp.text, "html.parser")

                    for span in soup.find_all("span"):
                        if match := re.match(r"(\s*)Title:(.*)", span.text):
                            name = match.group(2).strip()
                        if match := re.match(r"(\s*)Author[(]s[)]:(.*)", span.text):
                            authors = match.group(2).strip()
                        if match := re.match(r"(\s*)Publishing Organization:(.*)", span.text):
                            source = match.group(2).strip()
                    for list_item in soup.find_all("li"):
                        if match := re.match(r"(\s*)Publication Date:(.*)", list_item.text):
                            year = match.group(2).strip()
                else:
                    slug = "criticalmaas_09_cog_" + row["COG ID"][:16]
                    name = f'TA1 COG {row["COG ID"]}'

                writer.writerow(
                    {
                        "slug": slug,
                        "name": name,
                        "website_url": website_url,
                        "archive_url": archive_url,
                        "ref_title": name,
                        "ref_authors": authors,
                        "ref_year": year,
                        "ref_source": source,
                    }
                )


if __name__ == "__main__":
    main()
