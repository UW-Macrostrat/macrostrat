from pydantic import BaseModel, ConfigDict
from typing import Optional


class CommonModel(BaseModel):
    model_config = ConfigDict(extra='allow')

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


class LineworkModel(CommonModel):
    name: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None
