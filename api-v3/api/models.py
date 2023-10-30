
from typing import Optional

from pydantic import BaseModel, ConfigDict
from geojson_pydantic import Feature, Polygon


class CommonModel(BaseModel):
    model_config = ConfigDict(extra='allow')

    db_id: Optional[int] = None  # Primary Key
    source_id: Optional[int] = None
    orig_id: Optional[int] = None
    descrip: Optional[str] = None
    ready: Optional[bool] = None


class PolygonModel(CommonModel):
    name: Optional[str] = None
    strat_name: Optional[str] = None
    age: Optional[str] = None
    comments: Optional[str] = None
    t_interval: Optional[str] = None
    b_interval: Optional[str] = None
    geom: Optional[Polygon] = None


class LineworkModel(CommonModel):
    name: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None


# Database Models

class Sources(BaseModel):
    source_id: int
    name: str
    primary_table: str
    url: str
    ref_title: str
    authors: Optional[str] = None
    ref_year: str
    ref_source: str
    isbn_doi: Optional[str] = None
    scale: Optional[str] = None
    primary_line_table: Optional[str] = None
    licence: Optional[str] = None
    features: Optional[int] = None
    area: Optional[int] = None
    priority: bool
    rgeom: Optional[Polygon] = None
    display_scales: list[str] = None
    web_geom: Optional[Polygon] = None
    new_priority: int
    status_code: str

    class Config:
        orm_mode = True

