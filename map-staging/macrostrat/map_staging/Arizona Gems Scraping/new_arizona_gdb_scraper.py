import os
import random
import time
from urllib.parse import unquote, urljoin, urlparse
import re
import csv
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import zipfile

BASE_URL = "https://repository.arizona.edu"
START_URL = f"{BASE_URL}/handle/10150/628301/recent-submissions"
OUTPUT_DIR = "gdb_zips"

os.makedirs(OUTPUT_DIR, exist_ok=True)

SKIPPED_FILENAMES_PATH = "downloaded_gdb_files.txt"

# Load downloaded filenames into a set
downloaded_filenames = set()
if os.path.exists(SKIPPED_FILENAMES_PATH):
    with open(SKIPPED_FILENAMES_PATH) as f:
        downloaded_filenames = set(line.strip() for line in f)
PROCESSED_URLS_PATH = "processed_item_urls.csv"
CSV_HEADERS = [
    "filename_prefix",
    "url",
    "ref_title",
    "authors",
    "ref_year",
    "ref_source",
    "scale_denominator",
]

#inserts header row in csv
if not os.path.exists(PROCESSED_URLS_PATH) or os.path.getsize(PROCESSED_URLS_PATH) == 0:
    with open(PROCESSED_URLS_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)


visited_urls = set()
if os.path.exists(PROCESSED_URLS_PATH):
    with open(PROCESSED_URLS_PATH, newline="") as f:
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
            visited_urls.add(url)


def strip_gdb_zip_suffixes(filename: str) -> str:
    """
    Given something like 'BoulderMountain.gdb.zip', return 'BoulderMountain'.
    Handles .zip, .gdb, or .gdb.zip (case-insensitive).
    """
    name = filename
    for ext in [".zip", ".gdb"]:
        if name.lower().endswith(ext):
            name = name[: -len(ext)]
    return name

def extract_all_zips(root_dir=OUTPUT_DIR):
    """
    Extract all .zip files in root_dir into the same directory.
    For .gdb.zip files, this will create a .gdb folder next to the zip.
    """
    for name in os.listdir(root_dir):
        if not name.lower().endswith(".zip"):
            continue

        zip_path = os.path.join(root_dir, name)

        # Optional: skip if we've already extracted a .gdb folder with same prefix
        prefix = strip_gdb_zip_suffixes(name)  # e.g. BoulderMountain
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


def download_gdb_zips(item_url):
    '''Saves the filename along with the url link to the repository the files
    are extracted from.'''
    soup = get_soup(item_url)

    citation_text = get_citation_text(soup)
    citation_fields = parse_citation(citation_text)
    download_links = soup.select("a[href*='.gdb.zip']")
    download_urls = {urljoin(BASE_URL, a["href"]) for a in download_links}
    print(f"Checking {item_url} - found {len(download_links)} .gdb.zip links")

    downloaded_files = []

    for file_url in download_urls:
        parsed = urlparse(file_url)
        filename = os.path.basename(parsed.path)
        filename = unquote(filename)

        if filename in downloaded_filenames:
            print(f"Already scraped this file....skipping: {filename}")
            downloaded_files.append(filename)
            continue

        out_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(out_path):
            print(f"Already downloaded: {filename}")
            downloaded_files.append(filename)
            continue

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
            downloaded_files.append(filename)
        except Exception as e:
            print(f"Download failed for {filename}: {e}")
    return downloaded_files, citation_fields


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
    item_pages = get_all_item_links(START_URL)
    for idx, url in enumerate(tqdm(item_pages, desc="Items")):
        if url in visited_urls:
            continue  #skip already processed item
        try:
            files, citation_fields = download_gdb_zips(url)
            ref_title = citation_fields.get("ref_title") if citation_fields else ""
            authors = citation_fields.get("authors") if citation_fields else ""
            ref_year = citation_fields.get("ref_year") if citation_fields else ""
            ref_source = citation_fields.get("ref_source") if citation_fields else ""
            scale_den = (
                citation_fields.get("scale_denominator")
                if citation_fields and citation_fields.get("scale_denominator") is not None
                else ""
            )

            with open(PROCESSED_URLS_PATH, "a", newline="") as f:
                writer = csv.writer(f)
                if files:
                    for filename in files:
                        filename_prefix = strip_gdb_zip_suffixes(filename)
                        writer.writerow(
                            [filename_prefix, url, ref_title, authors, ref_year, ref_source, scale_den]
                        )
                else:
                    #mark URL as processed even if it has no files
                    writer.writerow(
                        ["", url, ref_title, authors, ref_year, ref_source, scale_den]
                    )

            visited_urls.add(url)
            time.sleep(random.uniform(4.0, 8.0))
            if idx > 0 and idx % 100 == 0:
                print(f"[Cooldown] Processed {idx} items, sleeping for 120 seconds...")
                time.sleep(120)
        except Exception as e:
            print("Error", url, e)

    extract_all_zips()

