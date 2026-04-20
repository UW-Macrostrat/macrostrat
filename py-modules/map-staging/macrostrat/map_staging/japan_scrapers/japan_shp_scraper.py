import csv
import os
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DOWNLOAD_DIR = Path("/Users/afromandi/Macrostrat/Maps/Japan/quad_series")
METADATA_CSV = Path(
    "/Users/afromandi/Macrostrat/Projects/macrostrat/py-modules/map-staging/"
    "macrostrat/map_staging/japan_scrapers/metadata.csv"
)
LOG_CSV = DOWNLOAD_DIR / "download_log.csv"

BASE_URL_TEMPLATE = "https://www.gsj.jp/Map/EN/geology4-{}.html"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

LOG_FIELDS = [
    "page_url",
    "map_name",
    "matched_skip_slug",
    "vector_url",
    "status",
]


def clean_filename(name: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    return re.sub(r'[<>:"/\\\\|?*]', "_", name)


def extract_zip(zip_path: Path, target_dir: Path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(target_dir)


def slugify_text(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = cleaned.replace("-", "_")
    cleaned = re.sub(r"[^\w\s_]", "", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def generate_slug_candidates(map_name: str) -> list[str]:
    base = slugify_text(map_name)
    candidates = []

    def add_candidate(value: str):
        value = value.strip("_")
        if not value:
            return
        slug = f"{value}_japan"
        if slug not in candidates:
            candidates.append(slug)

    add_candidate(base)

    parts = [p for p in base.split("_") if p]
    if len(parts) > 1:
        for part in parts:
            add_candidate(part)

    return candidates


def load_existing_slugs(metadata_csv: Path) -> set[str]:
    if not metadata_csv.exists():
        print(f"⚠️ metadata.csv not found: {metadata_csv}")
        return set()

    existing_slugs = set()
    with metadata_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = (row.get("slug") or "").strip()
            if slug:
                existing_slugs.add(slug)

    return existing_slugs


def should_skip_by_metadata_slug(
    map_name: str, existing_slugs: set[str]
) -> tuple[bool, str | None]:
    for candidate in generate_slug_candidates(map_name):
        if candidate in existing_slugs:
            return True, candidate
    return False, None


def get_map_name_from_row(row) -> str | None:
    id_anchor = row.find("a", id=True, title=True)
    if not id_anchor:
        return None

    map_title = id_anchor.get("title", "").strip()
    if not map_title:
        return None

    match = re.search(r"\s([A-Z][A-Z0-9&\-\s]+)$", map_title)
    if not match:
        return None

    map_name = match.group(1).strip()
    map_name = re.sub(r"\s+", " ", map_name)
    return map_name


def get_vector_links_from_row(row, page_url: str) -> list[str]:
    links = []
    for a_tag in row.find_all("a", href=True):
        href = a_tag["href"].strip()
        text = a_tag.get_text(" ", strip=True).lower()

        is_vector_zip = href.lower().endswith(".zip") and "/vct/" in href.lower()

        if is_vector_zip:
            full_url = href if href.startswith("http") else urljoin(page_url, href)
            if full_url not in links:
                links.append(full_url)
        elif href.lower().endswith(".zip") and "vector" in text:
            full_url = href if href.startswith("http") else urljoin(page_url, href)
            if full_url not in links:
                links.append(full_url)

    return links


def load_existing_log(log_csv: Path) -> dict[tuple[str, str, str], str]:
    """
    Returns a mapping:
      (page_url, map_name, vector_url) -> latest status
    """
    status_map = {}
    if not log_csv.exists():
        return status_map

    with log_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (
                (row.get("page_url") or "").strip(),
                (row.get("map_name") or "").strip(),
                (row.get("vector_url") or "").strip(),
            )
            status_map[key] = (row.get("status") or "").strip()

    return status_map


def should_process_item(
    page_url: str,
    map_name: str,
    vector_url: str,
    prior_status_map: dict[tuple[str, str, str], str],
) -> bool:
    """
    Skip items already completed successfully.
    Retry failed or unseen items.
    """
    key = (page_url, map_name, vector_url)
    prior_status = prior_status_map.get(key, "")

    completed_statuses = {
        "downloaded",
        "skipped_existing_slug",
        "skipped_existing_directory",
    }

    if prior_status in completed_statuses:
        return False

    return True


def append_log_row(
    page_url: str,
    map_name: str,
    matched_skip_slug: str | None,
    vector_url: str,
    status: str,
):
    with LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writerow(
            {
                "page_url": page_url,
                "map_name": map_name,
                "matched_skip_slug": matched_skip_slug or "",
                "vector_url": vector_url,
                "status": status,
            }
        )


def initialize_log_csv(log_csv: Path):
    if not log_csv.exists():
        with log_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            writer.writeheader()


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            )
        }
    )
    return session


def download_and_extract_vector_zip(
    session: requests.Session,
    zip_url: str,
    map_name: str,
    page_url: str,
    matched_skip_slug: str | None,
):
    safe_dirname = clean_filename(map_name)
    extract_path = DOWNLOAD_DIR / safe_dirname

    if extract_path.exists() and any(extract_path.iterdir()):
        print(f"✓ Already exists: {extract_path}")
        append_log_row(
            page_url=page_url,
            map_name=map_name,
            matched_skip_slug=matched_skip_slug,
            vector_url=zip_url,
            status="skipped_existing_directory",
        )
        return

    zip_filename = os.path.basename(zip_url)
    zip_path = DOWNLOAD_DIR / zip_filename
    temp_extract_path = DOWNLOAD_DIR / f"{safe_dirname}__tmp"

    print(f"⬇️ Downloading {map_name} from {zip_url}")
    try:
        resp = session.get(zip_url, timeout=90)
        resp.raise_for_status()

        with zip_path.open("wb") as f:
            f.write(resp.content)
        print(f"✅ Saved ZIP: {zip_path}")

        if temp_extract_path.exists():
            shutil.rmtree(temp_extract_path)
        temp_extract_path.mkdir(parents=True, exist_ok=True)

        extract_zip(zip_path, temp_extract_path)

        entries = list(temp_extract_path.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            if extract_path.exists():
                shutil.rmtree(extract_path)
            entries[0].rename(extract_path)
            temp_extract_path.rmdir()
        else:
            if extract_path.exists():
                shutil.rmtree(extract_path)
            temp_extract_path.rename(extract_path)

        print(f"📦 Extracted to: {extract_path}")
        append_log_row(
            page_url=page_url,
            map_name=map_name,
            matched_skip_slug=matched_skip_slug,
            vector_url=zip_url,
            status="downloaded",
        )

    except Exception as e:
        print(f"❌ Failed for {map_name}: {e}")
        append_log_row(
            page_url=page_url,
            map_name=map_name,
            matched_skip_slug=matched_skip_slug,
            vector_url=zip_url,
            status=f"failed: {e}",
        )

    finally:
        if zip_path.exists():
            zip_path.unlink(missing_ok=True)
        if temp_extract_path.exists():
            shutil.rmtree(temp_extract_path, ignore_errors=True)


def process_page(
    session: requests.Session,
    page_number: int,
    existing_slugs: set[str],
    prior_status_map: dict[tuple[str, str, str], str],
):
    page_url = BASE_URL_TEMPLATE.format(page_number)
    page_key = (page_url, "", "")
    prior_page_status = prior_status_map.get(page_key, "")

    if prior_page_status == "downloaded_page":
        print(f"✓ Already completed page: {page_url}")
        return

    print(f"\n🌐 Fetching HTML from {page_url}")

    try:
        resp = session.get(page_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed page geology4-{page_number}.html: {e}")
        append_log_row(
            page_url=page_url,
            map_name="",
            matched_skip_slug="",
            vector_url="",
            status=f"failed_page: {e}",
        )
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    found_any_vector = False

    for row in soup.find_all("tr"):
        map_name = get_map_name_from_row(row)
        if not map_name:
            continue

        vector_links = get_vector_links_from_row(row, page_url)
        if not vector_links:
            continue

        found_any_vector = True

        skip, matched_slug = should_skip_by_metadata_slug(map_name, existing_slugs)
        if skip:
            print(
                f"⏭️ Skipping {map_name} because metadata.csv contains slug: {matched_slug}"
            )
            for vector_link in vector_links:
                if not should_process_item(
                    page_url, map_name, vector_link, prior_status_map
                ):
                    continue
                append_log_row(
                    page_url=page_url,
                    map_name=map_name,
                    matched_skip_slug=matched_slug,
                    vector_url=vector_link,
                    status="skipped_existing_slug",
                )
            continue

        for vector_link in vector_links:
            if not should_process_item(
                page_url, map_name, vector_link, prior_status_map
            ):
                print(f"✓ Already handled: {map_name} | {vector_link}")
                continue

            download_and_extract_vector_zip(
                session=session,
                zip_url=vector_link,
                map_name=map_name,
                page_url=page_url,
                matched_skip_slug=matched_slug,
            )

    # Mark page as successfully visited so page fetch doesn't repeat forever
    append_log_row(
        page_url=page_url,
        map_name="",
        matched_skip_slug="",
        vector_url="",
        status="downloaded_page" if found_any_vector else "downloaded_page_no_vectors",
    )


def main():
    initialize_log_csv(LOG_CSV)

    existing_slugs = load_existing_slugs(METADATA_CSV)
    prior_status_map = load_existing_log(LOG_CSV)
    session = get_session()

    print(f"Loaded {len(existing_slugs)} existing slug(s) from metadata.csv")
    print(f"Loaded {len(prior_status_map)} existing log entrie(s) from {LOG_CSV}")

    for page_number in range(1, 17):
        process_page(
            session=session,
            page_number=page_number,
            existing_slugs=existing_slugs,
            prior_status_map=prior_status_map,
        )

    print(f"\n📝 Updated log CSV at: {LOG_CSV}")
    print("🏁 All complete.")


if __name__ == "__main__":
    main()
