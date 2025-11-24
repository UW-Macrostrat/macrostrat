import re
from pathlib import Path

import pandas as pd

BASE_ROOT = Path(__file__).resolve().parents[4]  # /Users/.../Projects/macrostrat
PROCESSED_ITEMS_CSV = (
    BASE_ROOT
    / "map-staging"
    / "macrostrat"
    / "map_staging"
    / "Arizona Gems Scraping"
    / "processed_item_urls.csv"
)
SLUG_SAFE_CHARS = re.compile(r"[^a-z0-9_]+")


def find_gis_files(
    directory: Path, filter: str | None = None
) -> tuple[list[Path], list[Path]]:
    """
    Recursively find GIS files in a directory, or treat a single file/directory as a GIS dataset.
    """
    gis_files = []
    excluded_files = []

    # If the given path is a single .gdb directory, just return it directly
    if directory.suffix == ".gdb" and directory.is_dir():
        return [directory], []

    # Otherwise, recursively search for files
    for path in directory.rglob("*"):
        if path.suffix.lower() in (".geojson", ".gpkg", ".shp"):
            gis_files.append(path)
        elif path.is_dir() and path.suffix == ".gdb":
            gis_files.append(path)

    for gis_file in gis_files:
        name = gis_file.name
        if filter == "polymer":
            if (
                name.startswith("polymer")
                and "_bbox" not in name
                and "_legend" not in name
            ):
                continue
            else:
                excluded_files.append(gis_file)
        elif filter == "ta1":
            if "_bbox" not in name and "_legend" not in name:
                continue
            else:
                excluded_files.append(gis_file)

    return gis_files, excluded_files


import re
from pathlib import Path

SLUG_SAFE_CHARS = re.compile(r"[^a-z0-9_]+")


def normalize_slug(prefix: str, path: Path) -> tuple[str, str, str]:
    """
    Normalize a slug and also return a human-readable name and the file extension.
    Returns:
        slug:  e.g. "arizona_adamsmesa"
        name:  e.g. "Adams Mesa, Arizona"
        ext:   e.g. ".gdb"
    """
    ext = path.suffix.lower()
    stem_for_slug = path.stem.lower()
    stem_for_slug = re.sub(r"\s+", "_", stem_for_slug.strip())
    clean_stem = SLUG_SAFE_CHARS.sub("", stem_for_slug)
    slug = f"{prefix}_{clean_stem}"

    # filename stem/prefix"
    filename = path.stem.replace("_", " ")
    # "AdamsMesa" -> "Adams Mesa"
    filename = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    region = prefix.replace("_", " ").title()
    name = f"{filename}, {region}"

    return slug, name, ext


def process_sources_metadata(slug: str, data_path: Path) -> dict | None:
    """
    Look up metadata for this map based on its filename_prefix in processed_item_urls.csv.

    Assumes:
      - data_path is something like /.../AdamsMesa.gdb or /.../AdamsMesa
      - processed_item_urls.csv has columns:
        filename_prefix,url,ref_title,authors,ref_year,ref_source,scale_denominator
    """
    filename_prefix = Path(data_path).stem

    if not PROCESSED_ITEMS_CSV.is_file():
        print(f"Error: processed_item_urls.csv not found at {PROCESSED_ITEMS_CSV}")
        return None
    try:
        df = pd.read_csv(PROCESSED_ITEMS_CSV)
    except Exception as e:
        print(f"Error reading {PROCESSED_ITEMS_CSV}: {e}")
        return None

    if "filename_prefix" not in df.columns:
        print(f"Error: 'filename_prefix' column not found in {PROCESSED_ITEMS_CSV}")
        return None
    match = df.loc[df["filename_prefix"] == filename_prefix]
    if match.empty:
        print(
            f"No metadata row in processed_item_urls.csv for filename_prefix='{filename_prefix}'"
        )
        return None
    row = match.iloc[0]

    def _safe_get(col):
        # return matched metadata row
        return row[col] if col in df.columns and pd.notna(row[col]) else None

    sources_mapping = {
        "slug": slug,
        "filename_prefix": filename_prefix,
        "url": _safe_get("url") or "",
        "ref_title": _safe_get("ref_title") or "",
        "authors": _safe_get("authors") or "",
        "ref_year": (
            int(row["ref_year"])
            if "ref_year" in df.columns and pd.notna(row["ref_year"])
            else None
        ),
        "ref_source": _safe_get("ref_source") or "",
        "scale_denominator": (
            int(row["scale_denominator"])
            if "scale_denominator" in df.columns and pd.notna(row["scale_denominator"])
            else None
        ),
    }

    return sources_mapping
