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

from . import notices


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
    axis_type: str = "age"
    rgeom: str | None = None


def read_metadata_sheet(data_file) -> pl.DataFrame:
    """The `metadata` sheet as two columns, `key` and `value`."""
    return pl.read_excel(
        data_file,
        sheet_name="metadata",
        read_options={"header_row": None, "column_names": ["key", "value"]},
    )


def get_metadata(data_file) -> Metadata:
    return metadata_from_df(read_metadata_sheet(data_file))


def metadata_from_df(df: pl.DataFrame) -> Metadata:
    """The metadata sheet, read as key/value rows down to the `Documentation` marker."""
    if "key" not in df.columns or "value" not in df.columns:
        # A sheet read with a header row: its first two columns are the pairs
        df = df.select(
            pl.col(df.columns[0]).alias("key"), pl.col(df.columns[1]).alias("value")
        )
    df = df.with_columns(pl.col("key").cast(pl.Utf8), pl.col("value").cast(pl.Utf8))
    # Drop everything below the "Documentation" row, where the template explains itself
    try:
        ix = df["key"].index_of("Documentation")
    except Exception:
        ix = None
    if ix is not None:
        df = df.slice(0, ix)
    metadata = {
        str(key).strip(): value
        for key, value in zip(df["key"], df["value"])
        if key is not None and str(key).strip()
    }
    return metadata_from_dict(metadata)


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


AXIS_TYPES = ("height", "depth", "age")

#: `col_type` as the workbook writes it, to the `macrostrat.cols.col_type` it is stored as.
#: `section` and `column` are the older names.
COL_TYPES = {
    "measured": "section",
    "composite": "column",
    "section": "section",
    "column": "column",
}


def parse_col_type(value, **where) -> str | None:
    """`col_type` as stored; `None` where it is not given or not recognised."""
    text = _text(value)
    if text is None:
        return None
    col_type = COL_TYPES.get(text.lower())
    if col_type is None:
        notices.warning(
            "unknown-column-type",
            f"col_type should be `measured` or `composite`, got {text!r}",
            column="col_type",
            **where,
        )
    return col_type


def parse_axis_type(value, **where) -> str | None:
    """`axis_type` as given, warning about a value the format does not define."""
    axis_type = _text(value)
    if axis_type is not None and axis_type not in AXIS_TYPES:
        notices.warning(
            "unknown-axis-type",
            f"axis_type should be `height`, `depth` or `age`, got {axis_type!r}; "
            "reading it as `height`",
            column="axis_type",
            **where,
        )
    return axis_type


def parse_fill_values(value, **where) -> bool | None:
    """`fill_values` as a flag; `None` where it is not given."""
    text = _text(value)
    if text is None:
        return None
    if text.lower() in ("y", "yes", "true"):
        return True
    if text.lower() not in ("n", "no", "false"):
        notices.warning(
            "unknown-fill-values",
            f"fill_values should be `y` or `n`, got {text!r}; filling is off",
            column="fill_values",
            **where,
        )
    return False


def metadata_from_dict(metadata: dict) -> Metadata:
    """Metadata from plain key/value pairs — the sheet's, or a JSON submission's."""
    project_name = _text(metadata.get("project_name"))
    project_id = _text(metadata.get("project_id"))
    project_slug = _text(metadata.get("project_slug"))
    # Ensure that project_id is a valid integer
    if project_id is not None:
        try:
            project_id = int(float(project_id))
        except ValueError:
            if project_slug is None:
                # Interpret the project_id as a slug
                project_slug = project_id
                project_id = None
            else:
                notices.warning(
                    "bad-project-id",
                    f"project_id must be an integer, got {project_id!r}; using the "
                    "project slug",
                    sheet="metadata",
                )
                project_id = None

    project = None
    if project_id or project_slug or project_name:
        project = ProjectIdentifier(id=project_id, slug=project_slug, name=project_name)

    col_type = parse_col_type(metadata.get("col_type"), sheet="metadata") or "column"

    default_axis_type = "age" if col_type == "column" else "height"
    axis_type = parse_axis_type(metadata.get("axis_type"), sheet="metadata")
    axis_type = axis_type or default_axis_type

    return Metadata(
        project=project,
        compiler=_text(metadata.get("compiler_name")),
        col_type=col_type,
        axis_type=axis_type,
        fill_values=bool(
            parse_fill_values(metadata.get("fill_values"), sheet="metadata")
        ),
        rgeom=_text(metadata.get("rgeom")),
    )
