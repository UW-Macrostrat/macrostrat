# Metadata
# project_name: Southern Naukluft mountains (generalized)
# compiler_name: Daven Quinn
# col_type: column
# axis_type: height
# fill_values: y
# b_int: Ediacaran
# t_int: Cambrian
# rgeom: POLYGON ((15.91375 -24.484649, 16.442625 -24.484649, 16.442625 -24.026397, 15.91375 -24.026397, 15.91375 -24.484649))
import sys
from dataclasses import dataclass
from typing import Optional

import polars as pl
from pydantic import BaseModel
from rich import print


class ProjectIdentifier(BaseModel):
    id: Optional[int] = None
    slug: Optional[str] = None
    name: Optional[str] = None

    # At least one of id, slug, or name must be provided
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        slug: Optional[str] = None,
        name: Optional[str] = None,
    ):
        super().__init__(id=id, slug=slug, name=name)
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


def warn(msg: str):
    print("[yellow]!! ")


def get_metadata(data_file) -> Metadata:
    df = pl.read_excel(
        data_file,
        sheet_name="metadata",
        read_options={"header_row": None, "column_names": ["key", "value"]},
    )
    # Drop everything below the "Documentation" row
    # Get index of the first occurrence of "Documentation" in the "key" column
    ix = df["key"].index_of("Documentation")
    df = df.slice(0, ix)

    # Turn the metadata into a dictionary
    metadata = dict(zip(df["key"], df["value"]))
    project = None
    print("Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    # Get project name
    project_name = metadata.get("project_name", None)
    project_id = metadata.get("project_id", None)
    project_slug = metadata.get("project_slug", None)
    # Ensure that project_id is a valid integer
    if project_id is not None:
        try:
            project_id = int(project_id)
        except ValueError:
            if project_slug is None:
                # Interpret the project_id as a slug

                project_slug = project_id
                project_id = None
            else:
                raise ValueError("project_id must be a valid integer")

    print(f"Project: {project_name} ({project_id}, {project_slug})")

    project = ProjectIdentifier(id=project_id, slug=project_slug, name=project_name)

    return Metadata(
        project=project,
        compiler=metadata.get("compiler_name"),
        col_type=metadata.get("col_type", "column"),
        fill_values=metadata.get("fill_values", "n").lower() in ["y", "yes", "true"],
        rgeom=metadata.get("rgeom"),
    )
