from pathlib import Path


def find_gis_files(
    directory: Path, filter: str | None = None
) -> tuple[list[Path], list[Path]]:
    """
    Recursively find GIS files in a directory, applying an optional ingestion filter.
    Returns a tuple (included_files, excluded_files).
    """
    gis_files = (
        list(directory.rglob("*.gdb"))
        + list(directory.rglob("*.geojson"))
        + list(directory.rglob("*.gpkg"))
        + list(directory.rglob("*.shp"))
    )
    gis_data = []
    excluded_data = []

    for gis_file in gis_files:
        name = gis_file.name
        if filter == "polymer":
            if (
                name.startswith("polymer")
                and "_bbox" not in name
                and "_legend" not in name
            ):
                gis_data.append(gis_file)
            else:
                excluded_data.append(gis_file)
        elif filter == "ta1":
            if "_bbox" not in name and "_legend" not in name:
                gis_data.append(gis_file)
            else:
                excluded_data.append(gis_file)
        else:
            gis_data.append(gis_file)

    return gis_data, excluded_data
