import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DOWNLOAD_LOG_CSV = Path(
    "/Users/afromandi/Macrostrat/Maps/Japan/quad_series/download_log.csv"
)
SHAPEFILES_DIR = Path("/Users/afromandi/Macrostrat/Maps/Japan/quad_series/")
OUTPUT_CSV = Path(
    "/Users/afromandi/Macrostrat/Projects/macrostrat/py-modules/map-staging/"
    "macrostrat/map_staging/japan_scrapers/metadata.csv"
)

CSV_FIELDS = [
    "slug",
    "name",
    "url",
    "ref_title",
    "authors",
    "ref_year",
    "ref_source",
    "isbn_doi",
    "license",
    "keywords",
    "scale_denominator",
    "language",
    "description",
]


def session_with_headers() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0 Safari/537.36"
            )
        }
    )
    return s


def normalize_map_name_for_matching(text: str) -> str:
    text = text.strip().upper()
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def get_with_retries(
    session: requests.Session,
    url: str,
    timeout: int = 30,
    max_attempts: int = 5,
    sleep_seconds: int = 3,
):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_error = e
            print(f"Attempt {attempt}/{max_attempts} failed for {url}: {e}")
            if attempt < max_attempts:
                time.sleep(sleep_seconds)

    raise last_error


def title_case_map_name(map_name: str, prefecture: str | None = None) -> str:
    cleaned_map = map_name.strip().replace("-", " ")
    cleaned_map = re.sub(r"\s+", " ", cleaned_map)

    if prefecture:
        cleaned_prefecture = prefecture.strip().replace("-", " ")
        cleaned_prefecture = re.sub(r"\s+", " ", cleaned_prefecture)
        return f"{cleaned_map.title()}, {cleaned_prefecture.title()}, Japan"

    return f"{cleaned_map.title()}, Japan"


def normalize_year(year_text: str) -> str:
    m = re.search(r"\b(18|19|20)\d{2}\b", year_text)
    return m.group(0) if m else ""


def build_ref_source(no_field: str) -> str:
    """
    Example:
      07［NIIGATA］-032 -> https://www.gsj.jp/Map/EN/docs/5man_doc/07/07_032.htm
      14［...］-087     -> https://www.gsj.jp/Map/EN/docs/5man_doc/14/14_087.htm
    """
    m = re.search(r"(\d{2}).*?-(\d{3})", no_field)
    if not m:
        return ""
    series_prefix, suffix = m.group(1), m.group(2)
    return f"https://www.gsj.jp/Map/EN/docs/5man_doc/{series_prefix}/{series_prefix}_{suffix}.htm"


def build_keywords(no_field: str, prefecture: str, series: str) -> str:
    values = [v.strip() for v in [no_field, prefecture, series] if v and v.strip()]
    return ";".join(values)


def extract_detail_fields(soup: BeautifulSoup) -> dict:
    text_lines = []
    for line in soup.get_text("\n", strip=True).splitlines():
        line = line.strip()
        if line:
            text_lines.append(line)

    joined = "\n".join(text_lines)

    patterns = {
        "Series": r"Series\s*(.+)",
        "No.": r"No\.\s*(.+)",
        "Map Name": r"Map Name\s*(.+)",
        "Explanatory": r"Explanatory\s*(.+)",
        "Author": r"Author\s*(.+)",
        "Publish Year": r"Publish Year\s*(.+)",
        "Publisher": r"Publisher\s*(.+)",
        "Prefecture": r"Prefecture\s*(.+)",
    }

    extracted = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, joined)
        extracted[key] = match.group(1).strip() if match else ""

    return extracted


def load_downloaded_rows(download_log_csv: Path) -> list[dict]:
    """
    Keep one row per successfully downloaded map.
    """
    if not download_log_csv.exists():
        raise FileNotFoundError(f"download_log.csv not found: {download_log_csv}")

    rows = []
    seen = set()

    with download_log_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = (row.get("status") or "").strip()
            page_url = (row.get("page_url") or "").strip()
            map_name = (row.get("map_name") or "").strip()

            if status != "downloaded":
                continue
            if not page_url or not map_name:
                continue

            key = (page_url, map_name)
            if key in seen:
                continue
            seen.add(key)

            rows.append(
                {
                    "page_url": page_url,
                    "map_name": map_name,
                }
            )

    return rows


def normalize_name_like_shapefile_dir(text: str, prefix: str | None = None) -> str:
    """
    Normalize a map name using the same rules as the shapefile directory renamer.

    Examples:
      KYOTO-SEIHOKUBU        -> Kyoto_Seihokubu
      WAKAYAMA & OZAKI       -> Wakayama_and_Ozaki
      SHIRIYA ZAKI           -> Shiriya_Zaki
      Japan_Kyoto_Seihokubu  -> Japan_Kyoto_Seihokubu   (if prefix='Japan')
    """
    name = text.strip()

    normalized_prefix = None
    if prefix:
        normalized_prefix = prefix.strip()
        normalized_prefix = re.sub(r"\s*&\s*", "_and_", normalized_prefix)
        normalized_prefix = re.sub(r"[\s-]+", "_", normalized_prefix)
        normalized_prefix = re.sub(r"_+", "_", normalized_prefix).strip("_")

        prefix_parts = []
        for part in normalized_prefix.split("_"):
            if part.lower() == "and":
                prefix_parts.append("and")
            else:
                prefix_parts.append(part.capitalize())
        normalized_prefix = "_".join(prefix_parts)

    if normalized_prefix:
        name = re.sub(
            rf"^(?:{re.escape(normalized_prefix)}_)+",
            "",
            name,
            flags=re.IGNORECASE,
        )

    name = re.sub(r"\s*&\s*", "_and_", name)
    name = re.sub(r"[\s-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")

    parts = []
    for part in name.split("_"):
        if part.lower() == "and":
            parts.append("and")
        else:
            parts.append(part.capitalize())

    name = "_".join(parts)

    if normalized_prefix:
        return f"{normalized_prefix}_{name}"
    return name


def get_slug_from_shapefiles_dir(map_name: str, shapefiles_dir: Path) -> str:
    """
    Match the downloaded map_name to a directory in shapefiles/ using the same
    normalization rules used when renaming directories.

    Example:
      webpage map_name: KYOTO-SEIHOKUBU
      directory:        Japan_Kyoto_Seihokubu
      slug:             japan_kyoto_seihokubu
    """
    normalized_target_dirname = normalize_name_like_shapefile_dir(
        map_name,
        prefix="Japan",
    )

    for path in shapefiles_dir.iterdir():
        if not path.is_dir():
            continue

        if path.name == normalized_target_dirname:
            return path.name.lower()

    return ""


def find_detail_url_from_index_page(
    session: requests.Session,
    page_url: str,
    target_map_name: str,
) -> str | None:
    """
    Find the detail-page URL for the given map_name on the given index page.
    """
    resp = get_with_retries(session, page_url, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    target_normalized = normalize_map_name_for_matching(target_map_name)

    for row in soup.find_all("tr"):
        id_anchor = row.find("a", id=True, title=True)
        if not id_anchor:
            continue

        map_title = id_anchor.get("title", "").strip()
        if not map_title:
            continue

        match = re.search(r"\s([A-Z][A-Z0-9&\-\s]+)$", map_title)
        if not match:
            continue

        row_map_name = normalize_map_name_for_matching(match.group(1))
        if row_map_name != target_normalized:
            continue

        for a_tag in row.find_all("a", href=True):
            href = a_tag["href"].strip()
            if re.search(r"\d{2}_\d{3}\.htm$", href):
                return href if href.startswith("http") else urljoin(page_url, href)

    return None


def scrape_map_detail(
    session: requests.Session,
    page_url: str,
    map_name: str,
    slug: str,
) -> dict | None:
    detail_url = find_detail_url_from_index_page(session, page_url, map_name)
    if not detail_url:
        print(f"Could not find detail page for {map_name} on {page_url}")
        return None

    resp = get_with_retries(session, detail_url, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")
    fields = extract_detail_fields(soup)
    map_name_raw = fields.get("Map Name", "").strip()
    prefecture_raw = fields.get("Prefecture", "").strip()

    if not map_name_raw:
        return None

    row = {
        "slug": slug,
        "name": title_case_map_name(map_name_raw, prefecture_raw),
        "url": page_url,
        "ref_title": fields.get("Explanatory", ""),
        "authors": fields.get("Author", ""),
        "ref_year": normalize_year(fields.get("Publish Year", "")),
        "ref_source": build_ref_source(fields.get("No.", "")),
        "isbn_doi": "",
        "license": fields.get("Publisher", ""),
        "keywords": build_keywords(
            fields.get("No.", ""),
            fields.get("Prefecture", ""),
            fields.get("Series", ""),
        ),
        "scale_denominator": 50000,
        "language": "Japanese, English",
        "description": fields.get("Explanatory", ""),
    }

    return row


def load_existing_metadata(output_csv: Path) -> list[dict]:
    if not output_csv.exists():
        return []

    with output_csv.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def merge_rows_by_slug(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """
    Update existing rows by slug; append new ones if slug not present.
    """
    existing_by_slug = {
        (row.get("slug") or "").strip(): row
        for row in existing_rows
        if (row.get("slug") or "").strip()
    }

    for row in new_rows:
        slug = (row.get("slug") or "").strip()
        if not slug:
            continue
        existing_by_slug[slug] = row

    merged = list(existing_by_slug.values())
    merged.sort(key=lambda r: (r.get("slug") or ""))
    return merged


def write_csv(rows: list[dict], output_csv: Path) -> None:
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    session = session_with_headers()

    downloaded_rows = load_downloaded_rows(DOWNLOAD_LOG_CSV)
    print(f"Found {len(downloaded_rows)} downloaded map entries in download_log.csv")

    scraped_rows = []
    unmatched = []

    for i, item in enumerate(downloaded_rows, start=1):
        page_url = item["page_url"]
        map_name = item["map_name"]

        slug = get_slug_from_shapefiles_dir(map_name, SHAPEFILES_DIR)
        if not slug:
            unmatched.append(
                {
                    "page_url": page_url,
                    "map_name": map_name,
                    "reason": "No matching directory in shapefiles/",
                }
            )
            print(f"[{i}] No matching shapefiles directory for {map_name}")
            continue

        try:
            row = scrape_map_detail(
                session=session,
                page_url=page_url,
                map_name=map_name,
                slug=slug,
            )
            if not row:
                unmatched.append(
                    {
                        "page_url": page_url,
                        "map_name": map_name,
                        "reason": "Could not scrape detail metadata",
                    }
                )
                print(f"[{i}] Failed metadata scrape for {map_name}")
                continue

            scraped_rows.append(row)
            print(f"[{i}] Processed: {map_name} -> {slug}")

        except Exception as e:
            unmatched.append(
                {
                    "page_url": page_url,
                    "map_name": map_name,
                    "reason": str(e),
                }
            )
            print(f"[{i}] Failed for {map_name}: {e}")

    existing_rows = load_existing_metadata(OUTPUT_CSV)
    merged_rows = merge_rows_by_slug(existing_rows, scraped_rows)
    write_csv(merged_rows, OUTPUT_CSV)

    print(f"\nWrote {len(merged_rows)} total rows to {OUTPUT_CSV.resolve()}")

    if unmatched:
        print("\nUnmatched / failed rows:")
        for item in unmatched:
            print(f"  - {item['map_name']} | {item['page_url']} | {item['reason']}")


if __name__ == "__main__":
    main()
