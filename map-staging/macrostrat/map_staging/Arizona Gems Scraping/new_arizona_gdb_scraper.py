import csv
import os
import random
import re
import time
import zipfile
from multiprocessing.pool import ExceptionWithTraceback
from typing import Optional
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

"""
BASE_URL = "https://repository.arizona.edu"
START_URL = f"{BASE_URL}/handle/10150/628301/recent-submissions"
SKIPPED_FILENAMES_PATH = "downloaded_gdb_files.txt"
# Load downloaded filenames into a set
downloaded_filenames = set()
if os.path.exists(SKIPPED_FILENAMES_PATH):
    with open(SKIPPED_FILENAMES_PATH) as f:
        downloaded_filenames = set(line.strip() for line in f)"""

OUTPUT_DIR = "collection_zips"
GDB_DIR = "gdb_zips"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(GDB_DIR, exist_ok=True)

SAVE_METADATA_PATH = "metadata.csv"
CSV_HEADERS = [
    "filename_prefix",
    "url",  # the original repository page (item_url)
    "ref_title",  # metadata title
    "authors",  # semicolon-joined list of author names
    "ref_year",  # numeric year or empty string
    "ref_source",  # UA Library handle (or equivalent)
    "isbn_doi",  # DOI or first API link href
    "license",  # license type string
    "series",  # e.g. DGM-209
    "keywords",  # semicolon-joined keyword names
    "language",  # language
    "description",  # abstract
]

# inserts header row in csv
if not os.path.exists(SAVE_METADATA_PATH) or os.path.getsize(SAVE_METADATA_PATH) == 0:
    with open(SAVE_METADATA_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

"""
visited_urls = set()
if os.path.exists(SAVE_METADATA_PATH):
    with open(SAVE_METADATA_PATH, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0] == "filename_prefix":
                continue
            if len(row) == 1:
                url = row[0].strip()
            else:
                url = row[1].strip()
            visited_urls.add(url)"""


def strip_gdb_zip_suffixes(name: str) -> str | None:
    if name.lower().endswith(".gdb.zip"):
        return name[: -len(".gdb.zip")]
    return None


def extract_all_zips(root_dir=OUTPUT_DIR):
    """
    Extract all .zip formatted_filenames in root_dir into the same directory.
    For .gdb.zip formatted_filenames, this will create a .gdb folder next to the zip.
    """
    for name in os.listdir(root_dir):
        if not name.lower().endswith(".zip"):
            continue
        zip_path = os.path.join(root_dir, name)
        prefix = strip_gdb_zip_suffixes(name)
        gdb_dir = os.path.join(root_dir, f"{prefix}.gdb")
        if os.path.exists(gdb_dir):
            print(f"Already extracted: {gdb_dir} (skipping {name})")
            continue

        print(f"Extracting {zip_path} -> {root_dir}")
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(root_dir)
        except Exception as e:
            print(f"Failed to extract {zip_path}: {e}")


def get_soup(url, retries=5):
    for attempt in range(retries):
        try:
            time.sleep(1.0)
            resp = requests.get(url)
            if resp.status_code == 429:
                delay = 30 * (2**attempt)
                print(f"429 Too Many Requests: {url}, retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                delay = 30 * (2**attempt)
                print(f"Retrying {url} after {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            else:
                raise e
    raise Exception(f"Failed to fetch {url} after {retries} retries")


def get_all_item_links(
    start_url, total_items=1700, per_page=100, cache_file="scraped_item_links.txt"
):
    if os.path.exists(cache_file):
        print(f"Loading item links from cache: {cache_file}")
        with open(cache_file) as f:
            return [line.strip() for line in f if line.strip()]
    links = []
    for offset in range(0, total_items, per_page):
        page_url = f"{start_url}?offset={offset}&rpp={per_page}"
        soup = get_soup(page_url)
        time.sleep(3.0)

        sel = (
            soup.select("div.artifact-title a")
            or soup.select("a.artifact-title")
            or soup.select("div.ds-artifact-item a")
        )
        for a in sel:
            href = a.get("href")
            if href and "/handle/" in href:
                full_url = urljoin(BASE_URL, href)
                links.append(full_url)
        print(f"Page offset={offset}, found {len(sel)} links")
    # Save to cache file
    with open(cache_file, "w") as f:
        for link in links:
            f.write(link + "\n")
    print(f"Total found: {len(links)} (saved to {cache_file})")
    return links


def parse_citation(citation: str) -> dict:
    """
    Parse a full citation string into maps.sources-style fields.

    Example input:
    'Skotnicki, S.J., 2024, Geologic Map of the Four Peaks 7.5' Quadrangle,
     Maricopa and Gila Counties, Arizona v.2. Arizona Geological Survey Open File
     Report, DGM-220, 1 map sheet, map scale 1:24,000, 35 p.'
    """
    fields = {
        "authors": None,
        "ref_year": None,
        "ref_title": None,
        "ref_source": None,
        "scale_denominator": None,
    }
    if not citation:
        return fields
    text = " ".join(citation.split())
    m = re.search(r"(\d{4})", text)
    if not m:
        return fields  # can't do much without a year anchor
    year = m.group(1)
    fields["ref_year"] = year
    before = text[: m.start()].rstrip(" ,")
    after = text[m.end() :].lstrip(" ,")
    fields["authors"] = before or None
    if "." in after:
        title_part, rest = after.split(".", 1)
        title = title_part.strip(" ,")
        rest = rest.lstrip(" ,")
    else:
        title = after.strip(" ,")
        rest = ""
    fields["ref_title"] = title or None
    scale_match = re.search(
        r"(?:map\s+scale\s+|scale\s+)?(1:\d[\d,]*)",
        text,
        flags=re.IGNORECASE,
    )
    if scale_match:
        scale_str = scale_match.group(1)
        try:
            denom_part = scale_str.split(":", 1)[1]  # '24,000'
            denom_int = int(denom_part.replace(",", ""))  # 24000
            fields["scale_denominator"] = denom_int
        except (IndexError, ValueError):
            pass

    source_text = rest
    if source_text:
        ms = re.search(r"map\s+scale", source_text, flags=re.IGNORECASE)
        if ms:
            source_text = source_text[: ms.start()].rstrip(" ,")
        fields["ref_source"] = source_text or None
    return fields


def get_citation_text(soup):
    """Extract the full bibliographic citation text from the page."""
    meta = soup.find("meta", attrs={"name": "DCTERMS.bibliographicCitation"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return None


def filename_to_title_param(filename: str) -> str:
    """
    Convert a gdb/gdb.zip filename to a title parameter for the API.

    Examples:
      'WildcatHill.gdb.zip' -> 'Wildcat+Hill'
      'Wildcat_Hill.gdb'    -> 'Wildcat+Hill'
      'Wildcat Hill.gdb'    -> 'Wildcat+Hill'
    """
    stem = strip_gdb_zip_suffixes(filename)
    stem = stem.replace("_", " ")
    stem = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    title_param = "+".join(stem.split(" "))
    return title_param


def get_collection_id(filename: str) -> Optional[str]:
    results = requests.get(
        "https://data.azgs.arizona.edu/api/v1/metadata?collection_group=ADGM&file_type=gisdata&latest=true"
    )
    results.raise_for_status()
    results = results.json()
    for collection in results.get("data", []):
        metadata = collection.get("metadata", {})
        files = metadata.get("files", [])
        for f in files:
            if f.get("name") == filename:
                return collection.get("collection_id")
    return None


def get_gis_collections() -> Optional[str]:
    results = requests.get(
        "https://data.azgs.arizona.edu/api/v1/metadata?collection_group=ADGM&file_type=gisdata&latest=true"
    )
    results.raise_for_status()
    return results.json()


def get_collection_metadata(collection_id: str, name: str) -> dict:
    results = requests.get(
        f"https://data.azgs.arizona.edu/api/v1/metadata/{collection_id}"
    )
    payload = results.json()

    coll = payload.get("data", {})
    meta = coll.get("metadata", {}) or {}
    meta_links = meta.get("links", []) or []
    top_links = coll.get("links", []) or []
    identifiers = meta.get("identifiers", {}) or {}
    license_info = meta.get("license", {}) or {}
    authors = [a.get("person") for a in meta.get("authors", []) if a.get("person")]
    keywords = [k.get("name") for k in meta.get("keywords", []) if k.get("name")]
    url = meta_links[0].get("url") if meta_links else None

    isbn_doi = identifiers.get("doi")
    if not isbn_doi and top_links:
        isbn_doi = top_links[0].get("href")
    license_type = license_info.get("type")
    year_raw = meta.get("year")
    try:
        ref_year = int(year_raw) if year_raw is not None else None
    except (ValueError, TypeError):
        ref_year = None
    description = meta.get("abstract") or ""
    if description:
        # Remove the entire boilerplate paragraph starting with "This geodatabase is part of..."
        # This pattern matches from "This geodatabase" through "U.S. Government."
        description = re.sub(
            r"\s*This geodatabase is part of a digital republication.*?U\.S\. Government\.",
            "",
            description,
            flags=re.DOTALL | re.IGNORECASE,
        )
        description = re.sub(r"\n+", " ", description)
        description = re.sub(r"\s+", " ", description).strip()

    required_fields = {
        "name": name,
        "url": url,
        "authors": authors,
        "ref_year": ref_year,
        "ref_title": meta.get("title"),
        "ref_source": f"https://data.azgs.arizona.edu/api/v1/collections/{collection_id}",
        "isbn_doi": isbn_doi,
        "license": license_type,
        "series": meta.get("series"),
        "keywords": keywords,
        "language": meta.get("language"),
        "description": description,
    }
    return required_fields


def unzip_files(zip_path: str, extract_dir: str | None = None):
    if extract_dir is None:
        extract_dir = os.path.splitext(zip_path)[0]  # folder with same name as zip
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)
    return extract_dir


def extract_nested_gdb_zips(collection_dir: str, filename: str) -> None:
    """
    Walk collection_dir, find any *.gdb.zip under gisdata/, and extract the
    GDB contents into GDB_DIR/<mapname>.gdb/.
    """
    os.makedirs(GDB_DIR, exist_ok=True)

    for root, dirs, files in os.walk(collection_dir):
        # Only process paths under a gisdata/* subtree
        if "gisdata" not in root.split(os.sep):
            continue
        for fname in files:
            if not fname.lower().endswith(".gdb.zip"):
                continue
            zip_path = os.path.join(root, fname)
            gdb_name = filename + ".gdb"
            # destination: GDB_DIR/WildcatHill.gdb
            out_dir = os.path.join(GDB_DIR, gdb_name)
            if os.path.exists(out_dir):
                print(f"GDB already extracted: {out_dir}")
                continue
            print(f"Extracting nested GDB: {zip_path} -> {out_dir}")
            os.makedirs(out_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(out_dir)
            except Exception as e:
                print(f"Failed to extract nested GDB {zip_path}: {e}")


def download_files_from_api(collection_id: str, filename: str) -> None:
    url = f"https://data.azgs.arizona.edu/api/v1/collections/{collection_id}"
    print(f"Requesting: {url}")

    # stream api response so we don't load the whole ZIP into memory
    resp = requests.get(url, stream=True)
    resp.raise_for_status()

    out_path = os.path.join(OUTPUT_DIR, filename)
    print(f"Downloading .gdb to: {out_path}")
    try:
        with open(out_path, "wb") as f:
            for pkg in resp.iter_content(chunk_size=8192):
                if pkg:
                    f.write(pkg)
        extract_dir = unzip_files(out_path)
        print(f"Unzipped files: {extract_dir}")
        extract_nested_gdb_zips(extract_dir, filename)
    except Exception as e:
        print(f"Could not download: {filename}, {collection_id}\n {e}")
    return


'''
def download_gdb_zips(item_url: str):
    """
    Download any .gdb.zip files on the page and record metadata in processed_item_urls.csv.
    Returns a list of filename_prefixes (e.g. 'WildcatHill').
    """
    soup = get_soup(item_url)

    download_links = soup.select("a[href*='.gdb.zip']")
    gdb_links = {urljoin(BASE_URL, a["href"]) for a in download_links}
    print(f"Checking {item_url} - found {len(download_links)} .gdb.zip links")

    filenames_formatted: list[str] = []

    for file_url in gdb_links:
        parsed = urlparse(file_url)
        filename = unquote(os.path.basename(parsed.path))  # e.g. 'WildcatHill.gdb.zip'
        filename_prefix = strip_gdb_zip_suffixes(filename)  # e.g. 'WildcatHill'
        download_ok = False
        if filename in downloaded_filenames:
            print(f"Already scraped this file... skipping: {filename}")
            download_ok = True
        elif os.path.exists(os.path.join(OUTPUT_DIR, filename)):
            print(f"Already downloaded on disk: {filename}")
            downloaded_filenames.add(filename)
            download_ok = True
        else:
            # trying downloading the gdb
            out_path = os.path.join(OUTPUT_DIR, filename)
            print(f"Downloading: {filename}")
            try:
                time.sleep(1.0)
                with requests.get(file_url, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(out_path, "wb") as f:
                        for chunk in r.iter_content(8192):
                            f.write(chunk)

                with open(SKIPPED_FILENAMES_PATH, "a") as log:
                    log.write(filename + "\n")
                downloaded_filenames.add(filename)
                download_ok = True
            except Exception as e:
                print(f"Download failed for {filename}: {e}")
                download_ok = False

        if not download_ok:
            print(
                f"Skipping metadata for {filename_prefix} because download failed and file is not present."
            )
            continue
        else:
            # Get metadata via API
            collection_id = get_collection_id(filename)
            metadata = get_collection_metadata(collection_id) if collection_id else None
            metadata_to_csv(metadata)
    return 
'''


def metadata_to_csv(metadata):
    authors_str = "; ".join(metadata["authors"]) if metadata["authors"] else ""
    keywords_str = "; ".join(metadata["keywords"]) if metadata["keywords"] else ""

    row = [
        metadata["name"],  # filename_prefix
        metadata["url"],  # url (original repo page)
        metadata["ref_title"] or "",  # ref_title
        authors_str,  # authors
        metadata["ref_year"] or "",  # ref_year
        metadata["ref_source"] or "",  # ref_source
        metadata["isbn_doi"] or "",  # isbn_doi
        metadata["license"] or "",  # license
        metadata["series"] or "",  # series
        keywords_str,  # keywords
        metadata["language"] or "",  # language
        metadata["description"] or "",  # description
    ]

    with open(SAVE_METADATA_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def deduplicate_file(path):
    if os.path.exists(path):
        with open(path) as f:
            unique = sorted(set(line.strip() for line in f if line.strip()))
        with open(path, "w") as f:
            for line in unique:
                f.write(line + "\n")


# metadata csv format: filename_prefix,url,ref_title,authors,ref_year,ref_source,scale_denominator
if __name__ == "__main__":
    # deduplicate_file("scraped_item_links.txt")
    # item_pages = get_all_item_links(START_URL)
    collections = get_gis_collections()
    for collection in collections.get("data", []):
        collection_id = collection.get("collection_id")
        meta = collection.get("metadata", {}) or {}
        files = meta.get("files", [])
        for f in files:
            filename = f.get("name")
            name = strip_gdb_zip_suffixes(filename)
            if name is not None:
                download_files_from_api(collection_id, name)
                metadata = get_collection_metadata(collection_id, name)
                metadata_to_csv(metadata)

                break

    """for idx, url in enumerate(tqdm(item_pages, desc="Items")):
        if url in visited_urls:
            continue  # skip already processed item
        try:
            download_gdb_zips(url)
            visited_urls.add(url)
            time.sleep(random.uniform(4.0, 8.0))
            if idx > 0 and idx % 100 == 0:
                print(f"[Cooldown] Processed {idx} items, sleeping for 120 seconds...")
                time.sleep(120)
        except Exception as e:
            print("Error", url, e)"""
