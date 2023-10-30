from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import VARCHAR, TEXT, INTEGER, ARRAY, BOOLEAN
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from geoalchemy2 import Geometry


class Base(DeclarativeBase):
    pass


class Sources(Base):
    __tablename__ = "sources"
    __table_args__ = {'schema': 'maps'}
    source_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(255))
    primary_table: Mapped[str] = mapped_column(VARCHAR(255))
    url: Mapped[str] = mapped_column(VARCHAR(255))
    ref_title: Mapped[str] = mapped_column(TEXT)
    authors: Mapped[str] = mapped_column(VARCHAR(255))
    ref_year: Mapped[str] = mapped_column(TEXT)
    ref_source: Mapped[str] = mapped_column(VARCHAR(255))
    isbn_doi: Mapped[str] = mapped_column(VARCHAR(100))
    scale: Mapped[str] = mapped_column(VARCHAR(20))
    primary_line_table: Mapped[str] = mapped_column(VARCHAR(50))
    licence: Mapped[str] = mapped_column(VARCHAR(100))
    features: Mapped[int] = mapped_column(INTEGER)
    area: Mapped[int] = mapped_column(INTEGER)
    priority: Mapped[bool] = mapped_column(BOOLEAN)
    rgeom: Mapped[str] = mapped_column(Geometry('POLYGON'))
    display_scales: Mapped[list[str]] = mapped_column(ARRAY(TEXT))
    web_geom: Mapped[str] = mapped_column(Geometry('POLYGON'))
    new_priority: Mapped[int] = mapped_column(INTEGER)
    status_code: Mapped[str] = mapped_column(TEXT)
