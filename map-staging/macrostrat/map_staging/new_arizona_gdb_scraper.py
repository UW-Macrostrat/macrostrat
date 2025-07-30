import requests, time, os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from tqdm import tqdm

BASE_URL = "https://repository.arizona.edu"
START_URL = f"{BASE_URL}/handle/10150/628301/recent-submissions"
OUTPUT_DIR = "gdb_zips"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_soup(url):
    time.sleep(0.5)
    resp = requests.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

def get_all_item_links(start_url, total_items=1524, per_page=20):
    links = []
    for offset in range(0, total_items, per_page):
        page_url = f"{start_url}?offset={offset}"
        soup = get_soup(page_url)
        # Try multiple selectors to capture the item link
        sel = soup.select("div.artifact-title a") or soup.select("a.artifact-title") or soup.select("div.ds-artifact-item a")
        for a in sel:
            href = a.get('href')
            if href and '/handle/' in href:
                links.append(urljoin(BASE_URL, href))
        print(f"Page offset={offset}, found {len(sel)} links")
    print(f"Total found: {len(links)}")
    return links

def download_gdb_zips(item_url):
    soup = get_soup(item_url)
    for a in soup.select("a[href$='.gdb.zip']"):
        file_url = urljoin(BASE_URL, a['href'])
        fn = os.path.basename(file_url)
        path = os.path.join(OUTPUT_DIR, fn)
        if os.path.exists(path):
            print(f"Exists: {fn}")
            continue
        print(f"Downloading {fn}")
        with requests.get(file_url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

if __name__ == "__main__":
    item_pages = get_all_item_links(START_URL)
    for item in tqdm(item_pages, desc="Items"):
        try:
            download_gdb_zips(item)
        except Exception as e:
            print("Error", item, e)
