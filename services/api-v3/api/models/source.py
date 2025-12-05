import json
from typing import Optional, Union

from geojson_pydantic import Feature, MultiPolygon, Polygon
from numpy import isnan
from pydantic import BaseModel, ConfigDict, field_validator


# Database Models
class Post(BaseModel):
    name: str
    primary_table: Optional[str] = None
    url: Optional[str] = None
    raster_url: Optional[str] = None
    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    ref_source: Optional[str] = None
    isbn_doi: Optional[str] = None
    scale: Optional[str] = None
    primary_line_table: Optional[str] = None
    license: Optional[str] = None
    features: Optional[int] = None
    area: Optional[int] = None
    priority: Optional[bool] = None
    display_scales: Optional[list[str]] = None
    new_priority: Optional[int] = None
    status_code: Optional[str] = None
    slug: Optional[str] = None


class Get(Post):
    source_id: int


class Patch(Post):
    name: Optional[str] = None
