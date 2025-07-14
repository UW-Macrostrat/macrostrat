from pathlib import Path
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
