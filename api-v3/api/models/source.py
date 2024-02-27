from typing import Optional, Union
import json

from geojson_pydantic import Feature, Polygon, MultiPolygon
from pydantic import BaseModel, ConfigDict, field_validator
from numpy import isnan


# Database Models
class Sources(BaseModel):
    source_id: int
    name: Optional[str] = None
    primary_table: str
    url: Optional[str] = None
    raster_url: Optional[str] = None
    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    ref_source: Optional[str] = None
    isbn_doi: Optional[str] = None
    scale: Optional[str] = None
    primary_line_table: Optional[str] = None
    licence: Optional[str] = None
    features: Optional[int] = None
    area: Optional[int] = None
    priority: bool
    display_scales: Optional[list[str]] = None
    new_priority: int
    status_code: str





