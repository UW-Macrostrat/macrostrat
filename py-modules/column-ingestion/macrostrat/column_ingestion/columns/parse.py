from dataclasses import dataclass, field

import polars as pl

from ..refs import parse_ref_ids
from ..units import Unit


@dataclass
class Column:
    id: int = -1
    group_id: int = -1
    local_id: str | None = None
    name: str | None = None
    description: str | None = None
    project_id: int | None = None
    status_code: str = "in process"
    col_type: str = "column"
    #: A point location, used when no polygon is supplied. `geometry.resolve_geometry`
    #: treats a polygon as authoritative when both are present.
    lat: float | None = None
    lng: float | None = None
    geom: str | None = None
    rgeom: str | None = None
    #: Workbook-local `ref_id`s this column cites, resolved to `refs.id` by `refs`.
    ref_ids: list[str] = field(default_factory=list)
    units: list[Unit] = field(default_factory=list)


def _as_float(value) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_column_data(data_file, meta) -> list[Column]:
    df = pl.read_excel(data_file, sheet_name="columns")

    df = df.rename(
        {
            "name": "col_name",
            "id": "col_id",
            "type": "col_type",
        },
        strict=False,
    )

    print(df.head())

    columns = []
    for row in df.iter_rows(named=True):

        geom = row.get("rgeom", getattr(meta, "rgeom", None))

        col = Column(
            # TODO: implement ID upgrading to handle existing columns
            local_id=str(row.get("col_id")),
            name=row.get("col_name"),
            description=row.get("description"),
            status_code=row.get(
                "status_code", getattr(meta, "status_code", "in process")
            ),
            col_type=row.get("col_type", getattr(meta, "col_type", "column")),
            lat=_as_float(row.get("lat")),
            lng=_as_float(row.get("lng")),
            ref_ids=parse_ref_ids(row.get("ref_ids")),
            geom=row.get("geom"),
            rgeom=geom,
        )
        columns.append(col)
    return columns
