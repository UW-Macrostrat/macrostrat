import datetime
from enum import Enum
from typing import Optional

import api.models.source as Sources
from api.schemas import IngestProcessTag, IngestState
from pydantic import BaseModel, ConfigDict, field_validator


class Post(BaseModel):
    state: Optional[IngestState] = None
    comments: Optional[str] = None
    source_id: Optional[int] = None
    map_id: Optional[str] = None
    tags: Optional[list[str]] = None

    class Config:
        orm_mode = True
        extra = "ignore"


class Get(Post):
    id: int
    created_on: datetime.datetime
    completed_on: Optional[datetime.datetime] = None
    source: Optional[Sources.Get] = None

    @field_validator("tags", mode="before")
    @classmethod
    def transform_tags(cls, v):
        if not v:
            return []

        if isinstance(v[0], IngestProcessTag):
            return [tag.tag for tag in v]

        return v


class Patch(Post):
    pass


class Tag(BaseModel):
    tag: str
