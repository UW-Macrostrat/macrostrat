import datetime
import enum
from typing import List

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    PrimaryKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    BOOLEAN,
    ENUM,
    INTEGER,
    JSONB,
    TEXT,
    VARCHAR,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# maps.sources
class Sources(Base):
    __tablename__ = "sources"
    __table_args__ = {"schema": "maps"}

    source_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(VARCHAR(255))
    primary_table: Mapped[str | None] = mapped_column(VARCHAR(255))
    url: Mapped[str | None] = mapped_column(VARCHAR(255))

    ref_title: Mapped[str | None] = mapped_column(TEXT)
    authors: Mapped[str | None] = mapped_column(VARCHAR(255))
    ref_year: Mapped[str | None] = mapped_column(TEXT)
    ref_source: Mapped[str | None] = mapped_column(VARCHAR(255))
    isbn_doi: Mapped[str | None] = mapped_column(VARCHAR(100))

    scale: Mapped[str | None] = mapped_column(VARCHAR(20))
    primary_line_table: Mapped[str | None] = mapped_column(VARCHAR(50))
    license: Mapped[str | None] = mapped_column(VARCHAR(100))

    features: Mapped[int | None] = mapped_column(INTEGER)
    area: Mapped[int | None] = mapped_column(INTEGER)
    priority: Mapped[bool] = mapped_column(BOOLEAN, default=False)

    rgeom: Mapped[str | None] = mapped_column(Geometry)
    display_scales: Mapped[list[str] | None] = mapped_column(ARRAY(TEXT))
    web_geom: Mapped[str | None] = mapped_column(Geometry)

    new_priority: Mapped[int] = mapped_column(INTEGER, default=0)
    status_code: Mapped[str] = mapped_column(TEXT, default="active")

    slug: Mapped[str] = mapped_column(TEXT, unique=True)

    raster_url: Mapped[str | None] = mapped_column(TEXT)
    scale_denominator: Mapped[int | None] = mapped_column(INTEGER)
    is_finalized: Mapped[bool] = mapped_column(BOOLEAN, default=False)
    lines_oriented: Mapped[bool | None] = mapped_column(BOOLEAN)
    date_finalized: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    ingested_by: Mapped[str | None] = mapped_column(TEXT)
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(TEXT))
    language: Mapped[str | None] = mapped_column(TEXT)
    description: Mapped[str | None] = mapped_column(VARCHAR)

    ingest_process: Mapped["IngestProcess"] = relationship(back_populates="source")


# storage.object
class SchemeEnum(enum.Enum):
    http = "http"
    s3 = "s3"


class Object(Base):
    __tablename__ = "object"
    __table_args__ = (
        UniqueConstraint("scheme", "host", "bucket", "key", name="unique_file"),
        {"schema": "storage"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scheme: Mapped[SchemeEnum] = mapped_column(Enum(SchemeEnum), nullable=False)
    host: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    bucket: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    key: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)

    source: Mapped[dict | None] = mapped_column(JSONB)
    mime_type: Mapped[str | None] = mapped_column(VARCHAR(255))
    sha256_hash: Mapped[str | None] = mapped_column(VARCHAR(255))

    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_on: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


# storage.map_files  (NEW! intersection table)
class MapFiles(Base):
    __tablename__ = "map_files"
    __table_args__ = {"schema": "storage"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    ingest_process_id: Mapped[int] = mapped_column(
        ForeignKey("maps_metadata.ingest_process.id", ondelete="CASCADE"),
        nullable=False,
    )

    object_id: Mapped[int] = mapped_column(
        ForeignKey("storage.object.id", ondelete="CASCADE"),
        nullable=False,
    )


# ingest enums
class IngestState(enum.Enum):
    pending = "pending"
    ingested = "ingested"
    prepared = "prepared"
    post_harmonization = "post_harmonization"
    failed = "failed"
    abandoned = "abandoned"


class IngestType(enum.Enum):
    raster = "raster"
    vector = "vector"
    ta1_output = "ta1_output"


# maps_metadata.ingest_process
class IngestProcess(Base):
    __tablename__ = "ingest_process"
    __table_args__ = {"schema": "maps_metadata"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    state: Mapped[IngestState | None] = mapped_column(
        ENUM(IngestState, name="ingest_state", schema="maps", native_enum=True),
        nullable=True,
    )

    comments: Mapped[str | None] = mapped_column(TEXT)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("maps.sources.source_id"))

    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_on: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    map_id: Mapped[str | None] = mapped_column(TEXT)
    type: Mapped[IngestType | None] = mapped_column(
        Enum(IngestType, name="ingest_type")
    )

    polygon_state: Mapped[dict | None] = mapped_column(JSONB)
    line_state: Mapped[dict | None] = mapped_column(JSONB)
    point_state: Mapped[dict | None] = mapped_column(JSONB)

    ingest_pipeline: Mapped[str | None] = mapped_column(TEXT)
    map_url: Mapped[str | None] = mapped_column(TEXT)
    ingested_by: Mapped[str | None] = mapped_column(TEXT)
    slug: Mapped[str | None] = mapped_column(TEXT)

    source: Mapped[Sources] = relationship(back_populates="ingest_process")

    tags: Mapped[List["IngestProcessTag"]] = relationship(
        back_populates="ingest_process"
    )


# maps_metadata.ingest_process_tag
class IngestProcessTag(Base):
    __tablename__ = "ingest_process_tag"
    __table_args__ = (
        PrimaryKeyConstraint("ingest_process_id", "tag", name="pk_tag"),
        {"schema": "maps_metadata"},
    )

    ingest_process_id: Mapped[int] = mapped_column(
        ForeignKey("maps_metadata.ingest_process.id", ondelete="CASCADE")
    )
    tag: Mapped[str] = mapped_column(VARCHAR(255))

    ingest_process: Mapped[IngestProcess] = relationship(back_populates="tags")
