import datetime
from typing import Optional

from api.schemas import SchemeEnum
from pydantic import BaseModel


class Base(BaseModel):
    source: Optional[dict] = None
    mime_type: Optional[str] = None
    sha256_hash: Optional[str] = None
    object_group_id: Optional[int] = None

    class Config:
        orm_mode = True


class Post(Base):
    scheme: SchemeEnum
    host: str
    bucket: str
    key: str

    class Config:
        orm_mode = True


class Get(Post):
    id: int
    created_on: datetime.datetime
    updated_on: datetime.datetime
    deleted_on: Optional[datetime.datetime] = None


class GetSecureURL(Get):
    pre_signed_url: str


class Patch(Base):
    object_group_id: Optional[int] = None
    created_on: Optional[datetime.datetime] = None
    updated_on: Optional[datetime.datetime] = None
    deleted_on: Optional[datetime.datetime] = None
