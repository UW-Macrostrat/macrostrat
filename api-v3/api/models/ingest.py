import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from api.schemas import IngestState, IngestProcessTag
import api.models.source as Sources


class Post(BaseModel):
    state: Optional[IngestState] = None
    comments: Optional[str] = None
    source_id: Optional[int] = None
    access_group_id: Optional[int] = None
    map_id: Optional[str] = None
    tags: Optional[list[str]] = None

    class Config:
        orm_mode = True
        extra = "ignore"


class Get(Post):
    id: int
    object_group_id: int
    created_on: datetime.datetime
    completed_on: Optional[datetime.datetime] = None
    source: Optional[Sources.Get] = None

    @field_validator("tags", mode="before")
    @classmethod
    def transform_tags(cls, v):
        if len(v) == 0:
            return []

        if isinstance(v[0], IngestProcessTag):
            return [tag.tag for tag in v]

        return v


class Patch(Post):
    pass


class Tag(BaseModel):
    tag: str
