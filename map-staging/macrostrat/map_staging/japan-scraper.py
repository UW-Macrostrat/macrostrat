import os
import re
import requests
import zipfile
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HTML_FILE = "/Users/afromandi/Macrostrat/Projects/macrostrat/map-staging/data/japan.html"
DOWNLOAD_DIR = "/Users/afromandi/Macrostrat/Maps/Japan/niigata_vector_data"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
URL = "https://www.gsj.jp/Map/EN/geology4-7.html"

def download_html():
    print(f"🌐 Fetching HTML from {URL}")
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"✅ Saved HTML to {HTML_FILE}")


def clean_filename(name):
    return re.sub(r"[^\w\-_. ]", "_", name).strip()

def extract_and_rename(zip_path, target_dir):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(target_dir)

def main():
    download_html()
    with open(HTML_FILE, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    for row in soup.find_all("tr"):
        id_anchor = row.find("a", id=True, title=True)
        if not id_anchor:
            continue

        map_id = id_anchor["id"]
        map_title = id_anchor["title"]
        match = re.search(r"\s([A-Z][A-Z]+[A-Z]?)$", map_title.strip())
        if not match:
            continue
        map_name = clean_filename(match.group(1))

        vector_link = None
        for a_tag in row.find_all("a", href=True):
            href = a_tag["href"]
            if "/VCT/" in href and href.endswith(".zip"):
                vector_link = href
                break

        if not vector_link:
            continue

        url = vector_link if vector_link.startswith("http") else urljoin("https://www.gsj.jp/Map/EN/geology4-6.html", vector_link)
        zip_filename = os.path.basename(url)
        zip_path = os.path.join(DOWNLOAD_DIR, zip_filename)
        extract_path = os.path.join(DOWNLOAD_DIR, map_name)

        if os.path.exists(extract_path):
            print(f"✓ Already exists: {extract_path}")
            continue

        print(f"⬇️ Downloading {map_name} from {url}")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            with open(zip_path, "wb") as f:
                f.write(resp.content)
            print(f"✅ Saved ZIP: {zip_path}")

            os.makedirs(extract_path, exist_ok=True)
            extract_and_rename(zip_path, extract_path)
            print(f"📦 Extracted to: {extract_path}")
            os.remove(zip_path)
        except Exception as e:
            print(f"❌ Failed for {map_name}: {e}")

    print("🏁 All complete.")

if __name__ == "__main__":
    main()
