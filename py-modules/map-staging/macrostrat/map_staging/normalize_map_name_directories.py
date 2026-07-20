import re
import shutil
from pathlib import Path


def normalize_map_directories(parent_path: Path, prefix: str | None = None) -> None:
    parent_path = Path(parent_path)

    if not parent_path.is_dir():
        raise ValueError(f"Not a valid directory: {parent_path}")

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

    for path in parent_path.iterdir():
        if not path.is_dir():
            continue

        name = path.name.strip()

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
            new_name = f"{normalized_prefix}_{name}"
        else:
            new_name = name

        new_path = path.with_name(new_name)

        if new_path == path:
            continue

        if new_path.exists():
            print(f"Skipping {path.name} -> {new_name} (target already exists)")
            continue

        path.rename(new_path)
        print(f"Renamed: {path.name} -> {new_name}")


def move_nested_shp_directories_to_shapefiles(parent_path: Path) -> None:
    """
    For each map directory in parent_path:
    - find the nested extracted shapefile directory
    - rename it to match the parent map directory name
    - move it into parent_path / 'shapefiles'
    """
    parent_path = Path(parent_path)
    if not parent_path.is_dir():
        raise ValueError(f"Not a valid directory: {parent_path}")

    shapefiles_dir = parent_path / "shapefiles"
    shapefiles_dir.mkdir(exist_ok=True)

    for map_dir in parent_path.iterdir():
        if not map_dir.is_dir():
            continue
        if map_dir.name == "shapefiles":
            continue

        subdirs = [p for p in map_dir.iterdir() if p.is_dir()]
        if not subdirs:
            print(f"Skipping {map_dir.name}: no nested directory found")
            continue

        if len(subdirs) > 1:
            print(
                f"Skipping {map_dir.name}: multiple nested directories found "
                f"({', '.join(p.name for p in subdirs)})"
            )
            continue

        nested_dir = subdirs[0]
        target_dir = shapefiles_dir / map_dir.name

        if target_dir.exists():
            print(f"Skipping {map_dir.name}: target already exists at {target_dir}")
            continue

        renamed_nested_dir = map_dir / map_dir.name
        if nested_dir.name != map_dir.name:
            nested_dir.rename(renamed_nested_dir)
            nested_dir = renamed_nested_dir
            print(f"Renamed nested dir: {renamed_nested_dir.name}")

        shutil.move(str(nested_dir), str(target_dir))
        print(f"Moved {map_dir.name} -> {target_dir}")


if __name__ == "__main__":
    base_dir = Path("/Users/afromandi/Macrostrat/Maps/Japan/quad_series")

    normalize_map_directories(base_dir, "Japan")
    move_nested_shp_directories_to_shapefiles(base_dir)
