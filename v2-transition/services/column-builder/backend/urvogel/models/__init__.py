from enum import Enum
from pydantic import BaseModel, Field
from geojson_pydantic import Point, Polygon, MultiPolygon

## geojson types for pydantic
## https://github.com/developmentseed/geojson-pydantic

## these are more for typing the queries than the actual db tables

class Project(BaseModel):
    id: int | None
    project: str
    descrip: str | None
    timescale_id: int | None

class ColumnGroup(BaseModel):
    id: int | None
    col_group: str
    col_group_long: str

class Column(BaseModel):
    id: int | None
    col_group_id: int
    project_id: int
    col_type: str | None = Field(default_factory= "column")
    status_code: str | None = Field(default_factory="in process")
    col_position: str | None
    col: int # seems like a unique int for every col_group
    col_name: str
    lat: float
    lng: float
    col_area: float
    coordinate: Point
    wkt: str | None
    created: str | None
    poly_geom: Polygon | MultiPolygon | None

class Unit(BaseModel):
    id: int | None
    strat_name: str
    color: str
    outcrop: str | None
    fo: int # bottom time period "older bound" - fk for interval
    name_fo: str | None # older bound interval name
    lo: int # top time period "younger bound" - fk for interval
    name_lo: str | None # younger bound interval name
    position_bottom: int
    position_top: int
    max_thick: int 
    min_thick : int
    section_id: int 
    col_id: int

class EnvironClass(str, Enum):
    marine="marine"
    non_marine = "non-marine"

class Environ(BaseModel):
    id: int | None
    environ: str
    environ_type: str | None
    environ_class: EnvironClass
    environ_color: str

class LithClass(str, Enum):
    sedimentary = "sedimentary"
    igneous = "igneous"
    metamorphic = "metamorphic"

class Lith(BaseModel): 
    id: int | None
    lith: str
    lith_group: str | None
    lith_type: str 
    lith_class: LithClass
    lith_fill: int
    comp_coef: float
    initial_porosity: float
    bulk_density: float
    lith_color: str

