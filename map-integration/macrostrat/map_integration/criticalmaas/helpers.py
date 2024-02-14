from pathlib import Path


def _unlink_if_exists(filename: Path, overwrite: bool = False):
    file_exists = filename.exists()
    if file_exists and not overwrite:
        raise FileExistsError(f"File {filename} already exists")

    if file_exists and overwrite:
        filename.unlink()
