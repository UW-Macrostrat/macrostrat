from typing import Optional, Union

from geojson_pydantic import Feature, Polygon, MultiPolygon
from pydantic import BaseModel, ConfigDict, field_validator
from numpy import isnan


class CommonModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: Optional[Union[int | str]] = None
    orig_id: Optional[Union[int | str]] = None
    descrip: Optional[str] = None
    omit: Optional[Union[bool | str]] = None


class LineStringModel(CommonModel):
    name: Optional[str] = None
    descrip: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None


class PointModel(CommonModel):
    strike: Optional[Union[int | str]] = None
    dip: Optional[Union[int | str]] = None
    dip_dir: Optional[Union[int | str]] = None
    point_type: Optional[str] = None
    certainty: Optional[str] = None
    comments: Optional[str] = None


class PolygonModel(CommonModel):
    name: Optional[str] = None
    strat_name: Optional[str] = None
    age: Optional[str] = None
    comments: Optional[str] = None
    t_interval: Optional[Union[int | str]] = None
    b_interval: Optional[Union[int | str]] = None
    confidence: Optional[Union[float | str]] = None
    t_age: Optional[Union[float | str]] = None
    b_age: Optional[Union[float | str]] = None


class PolygonRequestModel(PolygonModel):
    @field_validator("t_interval", "b_interval", "source_id", "orig_id")
    def transform_str_to_int(cls, v):
        if isinstance(v, str):
            return int(v)
        return v


class PolygonResponseModel(PolygonModel):
    @field_validator("confidence", "t_age", "b_age")
    def change_nan_to_none(cls, v):
        if type(v) == float and isnan(v):
            return None
        return v


class CopyColumnRequest(BaseModel):
    source_column: str
