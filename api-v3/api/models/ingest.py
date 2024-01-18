import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from api.models.object import Object


class IngestProcess(BaseModel):

    object_id: int
    comments: Optional[str] = None

    class Config:
        orm_mode = True
        extra = "ignore"


class ResponseIngestProcess(IngestProcess):
    id: int
    group_id: Optional[int] = None
    created_on: datetime.datetime
    completed_on: Optional[datetime.datetime] = None


class ResponseIngestProcessWithObject(ResponseIngestProcess):
    object: Object


class IngestProcessPatch(BaseModel):
    group_id: Optional[int] = None
    comments: Optional[str] = None
    completed_on: Optional[datetime.datetime] = None
