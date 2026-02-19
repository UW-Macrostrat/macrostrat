import re
from pathlib import Path

import geopandas as G
import pandas as pd

from macrostrat.core.database import get_database

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
    # base filename without extension, e.g. "SaddleMountain" from "SaddleMountain.gdb"
    stem_for_slug = path.stem.strip()
    stem_for_slug = re.sub(r"\s+", "_", stem_for_slug)
    stem_for_slug = stem_for_slug.lower()

    clean_stem = SLUG_SAFE_CHARS.sub("", stem_for_slug)
    clean_stem = re.sub(r"_+", "_", clean_stem).strip("_")

    slug = f"{prefix}_{clean_stem}"
    filename = path.stem.replace("_", " ")
    filename = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    region = prefix.replace("_", " ").title()
    name = f"{filename}, {region}"

    return slug, name, ext


def get_age_interval_df() -> pd.DataFrame:
    """Query and store interval names from the database into a DataFrame for lookups.
    Returns:
    pd.DataFrame. A pandas series with interval_name strings.
    """
    db = get_database()
    query = "SELECT id, interval_name FROM macrostrat.intervals"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def get_strat_names_df() -> pd.DataFrame:
    """Query and store interval names from the database into a DataFrame for lookups.
    Returns:
    pd.DataFrame. A pandas series with interval_name strings.
    """
    db = get_database()
    query = "select rank_name from macrostrat.lookup_strat_names"
    with db.engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


# standard map age function. User gets to input their column 1 and a column 2 data to map to our ages.
def map_t_b_standard(
    meta_df: G.GeoDataFrame, col_one: str, col_two: str
) -> G.GeoDataFrame:
    interval_df = get_age_interval_df().reset_index(drop=True)
    interval_lookup = {
        str(row["interval_name"]).strip().lower(): int(row["id"])
        for _, row in interval_df.iterrows()
    }

    # Ensure columns exist (prevents KeyError)
    if "b_interval" not in meta_df.columns:
        meta_df["b_interval"] = pd.NA
    if "t_interval" not in meta_df.columns:
        meta_df["t_interval"] = pd.NA

    if col_one in meta_df.columns:
        mapped_col_one = (
            meta_df[col_one]
            .astype("string")
            .str.strip()
            .str.lower()
            .replace("", pd.NA)
            .map(interval_lookup)
        )
        meta_df["b_interval"] = mapped_col_one
        meta_df["t_interval"] = mapped_col_one

    # fallback to map col_two if col_one row is empty
    if col_two in meta_df.columns:
        needs_fill = meta_df["b_interval"].isna() | meta_df["t_interval"].isna()
        if needs_fill.any():
            mapped_col_two = (
                meta_df.loc[needs_fill, col_two]
                .astype("string")
                .str.strip()
                .str.lower()
                .replace("", pd.NA)
                .map(interval_lookup)
            )
            meta_df.loc[needs_fill, "b_interval"] = mapped_col_two
            meta_df.loc[needs_fill, "t_interval"] = mapped_col_two

    if "era" in meta_df.columns:
        needs_fill = meta_df["b_interval"].isna() | meta_df["t_interval"].isna()
        if needs_fill.any():
            mapped_col_three = (
                meta_df.loc[needs_fill, "era"]
                .astype("string")
                .str.strip()
                .str.lower()
                .replace("", pd.NA)
                .map(interval_lookup)
            )
            meta_df.loc[needs_fill, "b_interval"] = mapped_col_three
            meta_df.loc[needs_fill, "t_interval"] = mapped_col_three

    return meta_df


def process_sources_metadata(
    slug: str, region_path: Path, parent: Path | None
) -> dict | None:
    """
    Load metadata for this map from metadata.csv.

    Expected columns in metadata.csv:
      filename_prefix,url,ref_title,authors,ref_year,ref_source,
      isbn_doi,license,keywords,language,description
    """
    filename_prefix = region_path.stem
    if parent is None:
        parent = region_path.parent

    metadata_csv = parent / "metadata.csv"

    if not metadata_csv.is_file():
        print(f"Error: metadata CSV not found at {metadata_csv}")
        return None

    try:
        df = pd.read_csv(metadata_csv)
    except Exception as e:
        print(f"Error reading {metadata_csv}: {e}")
        return None

    if "filename_prefix" not in df.columns:
        print(f"Error: 'filename_prefix' column missing in {metadata_csv}")
        return None

    match = df.loc[df["filename_prefix"] == filename_prefix]
    if match.empty:
        print(f"No metadata found for filename_prefix='{filename_prefix}'")
        return None

    row = match.iloc[0]

    def _safe(col):
        return row[col] if col in df.columns and pd.notna(row[col]) else None

    # normalize keywords: split on semicolon, trim, drop empties
    raw_keywords = _safe("keywords")
    keywords_list = (
        [kw.strip() for kw in raw_keywords.split(";") if kw.strip()]
        if isinstance(raw_keywords, str)
        else []
    )

    return {
        "slug": slug,
        "filename_prefix": filename_prefix,
        "url": _safe("url") or "",
        "ref_title": _safe("ref_title") or "",
        "authors": _safe("authors") or "",
        "ref_year": int(row["ref_year"]) if pd.notna(_safe("ref_year")) else None,
        "ref_source": _safe("ref_source") or "",
        "isbn_doi": _safe("isbn_doi") or "",
        "license": _safe("license") or "",
        "keywords": keywords_list,  # ARRAY
        "language": _safe("language") or "",
        "description": _safe("description") or "",
    }
