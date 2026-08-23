import datetime
from enum import Enum
from typing import Optional

import api.models.source as Sources
from api.schemas import IngestProcessTag
from pydantic import BaseModel, ConfigDict, field_validator


class Post(BaseModel):
    # Free text — validated by the FK to maps_metadata.ingest_state, not here.
    state: Optional[str] = None
    comments: Optional[str] = None
    source_id: Optional[int] = None
    # Commented out alongside the ORM column — `create_ingest_process` passes
    # `model_dump()` straight to IngestProcess(...), so a field with no matching
    # mapped column raises a TypeError.
    # map_id: Optional[str] = None
    tags: Optional[list[str]] = None

    class Config:
        orm_mode = True
        extra = "ignore"


class Get(Post):
    # `source_id` (inherited from Post) is the identity — the surrogate `id`
    # column was dropped when ingest_process was re-keyed on source_id.
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
