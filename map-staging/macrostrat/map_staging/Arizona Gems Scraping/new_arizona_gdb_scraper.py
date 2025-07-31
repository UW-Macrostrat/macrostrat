import requests, time, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
import random
from tqdm import tqdm

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
PROCESSED_URLS_PATH = "processed_item_urls.txt"

# Load visited item URLs
visited_urls = set()
if os.path.exists(PROCESSED_URLS_PATH):
    with open(PROCESSED_URLS_PATH) as f:
        visited_urls = set(line.strip() for line in f if line.strip())


def get_soup(url, retries=5):
    for attempt in range(retries):
        try:
            time.sleep(1.0)
            resp = requests.get(url)
            if resp.status_code == 429:
                delay = 30 * (2 ** attempt)
                print(f"429 Too Many Requests: {url}, retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                delay = 30 * (2 ** attempt)
                print(f"Retrying {url} after {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
                continue
            else:
                raise e
    raise Exception(f"Failed to fetch {url} after {retries} retries")


def get_all_item_links(start_url, total_items=1700, per_page=100, cache_file="scraped_item_links.txt"):
    if os.path.exists(cache_file):
        print(f"Loading item links from cache: {cache_file}")
        with open(cache_file) as f:
            return [line.strip() for line in f if line.strip()]
    links = []
    for offset in range(0, total_items, per_page):
        page_url = f"{start_url}?offset={offset}&rpp={per_page}"
        soup = get_soup(page_url)
        time.sleep(3.0)

        sel = soup.select("div.artifact-title a") or soup.select("a.artifact-title") or soup.select("div.ds-artifact-item a")
        for a in sel:
            href = a.get('href')
            if href and '/handle/' in href:
                full_url = urljoin(BASE_URL, href)
                links.append(full_url)
        print(f"Page offset={offset}, found {len(sel)} links")
    # Save to cache file
    with open(cache_file, "w") as f:
        for link in links:
            f.write(link + "\n")
    print(f"Total found: {len(links)} (saved to {cache_file})")
    return links


def download_gdb_zips(item_url):
    soup = get_soup(item_url)
    download_links = soup.select("a[href*='.gdb.zip']")
    download_urls = {urljoin(BASE_URL, a['href']) for a in download_links}
    print(f"Checking {item_url} - found {len(download_links)} .gdb.zip links")
    for file_url in download_urls:
        parsed = urlparse(file_url)
        filename = os.path.basename(parsed.path)
        filename = unquote(filename)

        if filename in downloaded_filenames:
            print(f"Already scraped this file....skipping: {filename}")
            continue

        out_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(out_path):
            print(f"Already downloaded: {filename}")
            continue

        print(f"Downloading: {filename}")
        try:
            time.sleep(1.0)
            with requests.get(file_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(out_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)

            with open(SKIPPED_FILENAMES_PATH, "a") as log:
                log.write(filename + "\n")
            downloaded_filenames.add(filename)
        except Exception as e:
            print(f"Download failed for {filename}: {e}")

def deduplicate_file(path):
    if os.path.exists(path):
        with open(path) as f:
            unique = sorted(set(line.strip() for line in f if line.strip()))
        with open(path, "w") as f:
            for line in unique:
                f.write(line + "\n")


if __name__ == "__main__":
    #deduplicate_file("scraped_item_links.txt")
    item_pages = get_all_item_links(START_URL)
    for idx, item in enumerate(tqdm(item_pages, desc="Items")):
        if item in visited_urls:
            continue  # Skip already processed item
        try:
            download_gdb_zips(item)
            with open(PROCESSED_URLS_PATH, "a") as f:
                f.write(item + "\n")
            visited_urls.add(item)

            time.sleep(random.uniform(4.0, 8.0))
            if idx > 0 and idx % 100 == 0:
                print(f"[Cooldown] Processed {idx} items, sleeping for 120 seconds...")
                time.sleep(120)

        except Exception as e:
            print("Error", item, e)
