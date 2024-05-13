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
            ],
        )
        writer.writeheader()

        for row in reader:
            if row["Process?"].lower() == "yes":
                archive_url = (
                    "https://s3.amazonaws.com/public.cdr.land/results/" + row["COG ID"] + ".zip"
                )
                website_url = row["NGMDB Product Link"]

                resp = requests.get(website_url, timeout=TIMEOUT)
                soup = bs4.BeautifulSoup(resp.text, "html.parser")

                name = f'TA1 NGMDB {row["NGMDB ProdID"]}'
                slug = "criticalmaas_09_ngmdb_" + row["NGMDB ProdID"]

                for span in soup.find_all("span"):
                    if span.text.startswith("Title:"):
                        if match := re.match(r"(\s*)Title:(.*)", span.text):
                            name = match.group(2).strip()

                writer.writerow(
                    {
                        "slug": slug,
                        "name": name,
                        "website_url": website_url,
                        "archive_url": archive_url,
                    }
                )


if __name__ == "__main__":
    main()
