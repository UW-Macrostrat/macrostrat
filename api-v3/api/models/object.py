import datetime
from typing import Optional

from pydantic import BaseModel

from api.schemas import SchemeEnum


class Object(BaseModel):
    scheme: SchemeEnum
    host: str
    bucket: str
    key: str
    source: dict
    mime_type: str
    sha256_hash: str

    class Config:
        orm_mode = True


class ResponseObject(Object):
    id: int
    created_on: datetime.datetime
    updated_on: datetime.datetime
    deleted_on: Optional[datetime.datetime] = None
