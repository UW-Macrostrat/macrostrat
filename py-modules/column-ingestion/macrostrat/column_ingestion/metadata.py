# Metadata
# project_name: Southern Naukluft mountains (generalized)
# compiler_name: Daven Quinn
# col_type: column
# axis_type: height
# fill_values: y
# b_int: Ediacaran
# t_int: Cambrian
# rgeom: POLYGON ((15.91375 -24.484649, 16.442625 -24.484649, 16.442625 -24.026397, 15.91375 -24.026397, 15.91375 -24.484649))

from dataclasses import dataclass
from typing import Optional

import polars as pl
from pydantic import BaseModel


class ProjectIdentifier(BaseModel):
    id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None

    # At least one of id, slug, or name must be provided
    def __init__(self, **data):
        super().__init__(**data)
        if not (self.id or self.slug or self.name):
            raise ValueError("At least one of id, slug, or name must be provided")


@dataclass
class Metadata:
    project: ProjectIdentifier | None
    compiler: str | None = None
    # Default column type
    col_type: str = "column"
    fill_values: bool = False
    rgeom: str | None = None


def get_metadata(data_file) -> Metadata:
    df = pl.read_excel(
        data_file,
        sheet_name="metadata",
        read_options={"header_row": None, "column_names": ["key", "value"]},
    )
    # Turn the metadata into a dictionary
    metadata = dict(zip(df["key"], df["value"]))
    project = None
    print("Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
        if key == "project_name":
            project = ProjectIdentifier(name=value)

    return Metadata(
        project=project,
        compiler=metadata.get("compiler_name"),
        col_type=metadata.get("col_type", "column"),
        fill_values=metadata.get("fill_values", "n").lower() in ["y", "yes", "true"],
        rgeom=metadata.get("rgeom"),
    )
