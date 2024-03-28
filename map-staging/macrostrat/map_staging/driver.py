"""
Ingest maps listed in a CSV file.
"""

import csv
import logging
import pathlib
import sys

import requests
from macrostrat.map_integration import config  # type: ignore[import-untyped]
from macrostrat.map_integration.errors import IngestError  # type: ignore[import-untyped]
from macrostrat.map_integration.pipeline import run_pipeline  # type: ignore[import-untyped]

DOWNLOAD_ROOT_DIR = pathlib.Path("./tmp")
FIELDS = [
    "slug",
    "name",
    "ref_title",
    "ref_authors",
    "ref_year",
    "ref_source",
    "ref_isbn_or_doi",
    "scale",
    "url",
    "website",
    "s3_bucket",
    "s3_prefix",
]


class UserError(RuntimeError):
    """
    A runtime error where a stack trace should not be necessary.
    """


# --------------------------------------------------------------------------


def init_logging() -> None:
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s %(message)s",
        level=logging.INFO,
        stream=sys.stderr,
    )


def main() -> None:
    input_file = sys.argv[1]

    with open(input_file, mode="r", encoding="utf-8", newline="") as input_fp:
        reader = csv.DictReader(input_fp)

        for row in reader:
            url = row["url"]
            prefix = row.get("s3_prefix") or "map_staging_driver"

            download_dir = DOWNLOAD_ROOT_DIR / prefix
            download_dir.mkdir(parents=True, exist_ok=True)

            filename = url.split("/")[-1]
            partial_local_file = download_dir / (filename + ".partial")
            local_file = download_dir / filename

            if not local_file.exists():
                response = requests.get(url, stream=True, timeout=config.TIMEOUT)
                response.raise_for_status()

                with open(partial_local_file, mode="wb") as local_fp:
                    for chunk in response.iter_content(chunk_size=config.CHUNK_SIZE):
                        local_fp.write(chunk)
                partial_local_file.rename(local_file)

            kwargs = {}
            for f in FIELDS:
                if row.get(f) is not None:
                    kwargs[f] = row[f]
            try:
                run_pipeline(local_file, **kwargs)
            except IngestError:
                logging.exception("Failed to process map completely")


def entrypoint() -> None:
    try:
        init_logging()
        main()
    except UserError as exn:
        print("ERROR:", *exn.args)
        sys.exit(1)
    except Exception:  # pylint: disable=broad-except
        logging.exception("Uncaught exception")
        sys.exit(1)


if __name__ == "__main__":
    entrypoint()
