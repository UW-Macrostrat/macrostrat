import os
from typing import Optional

from geojson_pydantic import Feature, Polygon
from pydantic import BaseModel, ConfigDict
from werkzeug.security import check_password_hash, generate_password_hash


class CommonModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_id: Optional[str |int] = None
    orig_id: Optional[str |int] = None
    descrip: Optional[str] = None
    ready: Optional[bool] = None


class PolygonModel(CommonModel):
    name: Optional[str] = None
    strat_name: Optional[str] = None
    age: Optional[str] = None
    comments: Optional[str] = None
    t_interval: Optional[str | int] = None
    b_interval: Optional[str | int] = None
    geom: Optional[Polygon] = None


class LineworkModel(CommonModel):
    name: Optional[str] = None
    type: Optional[str] = None
    direction: Optional[str] = None


# Database Models


class Sources(BaseModel):
    source_id: int
    name: Optional[str] = None
    primary_table: str
    url: Optional[str] = None
    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    ref_source: Optional[str] = None
    isbn_doi: Optional[str] = None
    scale: Optional[str] = None
    primary_line_table: Optional[str] = None
    licence: Optional[str] = None
    features: Optional[int] = None
    area: Optional[int] = None
    priority: bool
    rgeom: Optional[Polygon] = None
    display_scales: Optional[list[str]] = None
    web_geom: Optional[Polygon] = None
    new_priority: int
    status_code: str

    class Config:
        orm_mode = True


class User(BaseModel):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    # Columns are automagically mapped from database
    # *NEVER* directly set the password column.

    def set_password(self, plaintext):
        salt = os.environ["PASSWORD_SALT"]
        self.password = generate_password_hash(salt + str(plaintext))

    def is_correct_password(self, plaintext):
        salt = os.environ["PASSWORD_SALT"]
        return check_password_hash(self.password, salt + str(plaintext))
