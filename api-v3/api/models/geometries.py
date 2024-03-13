from typing import Optional, Union

from geojson_pydantic import Feature, Polygon, MultiPolygon
from pydantic import BaseModel, ConfigDict, field_validator
from numpy import isnan


class CommonModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: Optional[Union[int | str]] = None
    orig_id: Optional[Union[int | str]] = None
    descrip: Optional[str] = None
    ready: Optional[Union[bool | str]] = None


class PolygonModel(CommonModel):
    name: Optional[str] = None
    strat_name: Optional[str] = None
    age: Optional[str] = None
    comments: Optional[str] = None
    t_interval: Optional[Union[int | str]] = None
    b_interval: Optional[Union[int | str]] = None
    confidence: Optional[float] = None
    t_age: Optional[float] = None
    b_age: Optional[float] = None


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


class LineworkModel(CommonModel):
    name: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None


class CopyColumnRequest(BaseModel):
    source_column: str
