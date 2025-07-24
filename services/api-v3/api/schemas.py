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
    JSON,
    JSONB,
    TEXT,
    VARCHAR,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Sources(Base):
    __tablename__ = "sources"
    __table_args__ = {"schema": "maps"}
    source_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(255))
    primary_table: Mapped[str] = mapped_column(VARCHAR(255))
    url: Mapped[str] = mapped_column(VARCHAR(255))
    raster_url: Mapped[str] = mapped_column(VARCHAR(255))
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
    rgeom: Mapped[str] = mapped_column(Geometry("POLYGON"))
    display_scales: Mapped[list[str]] = mapped_column(ARRAY(TEXT))
    web_geom: Mapped[str] = mapped_column(Geometry("POLYGON"))
    new_priority: Mapped[int] = mapped_column(INTEGER)
    status_code: Mapped[str] = mapped_column(TEXT)
    slug: Mapped[str] = mapped_column(VARCHAR(255))

    # Relationship
    ingest_process: Mapped["IngestProcess"] = relationship(back_populates="source")


class GroupMembers(Base):
    __tablename__ = "group_members"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("macrostrat_auth.group.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("macrostrat_auth.user.id"))


class Group(Base):
    __tablename__ = "group"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(VARCHAR(255))
    users: Mapped[List["User"]] = relationship(
        secondary="macrostrat_auth.group_members",
        lazy="joined",
        back_populates="groups",
    )


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub: Mapped[str] = mapped_column(VARCHAR(255))
    name: Mapped[str] = mapped_column(VARCHAR(255))
    email: Mapped[str] = mapped_column(VARCHAR(255))
    groups: Mapped[List[Group]] = relationship(
        secondary="macrostrat_auth.group_members", lazy="joined", back_populates="users"
    )
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Token(Base):
    __tablename__ = "token"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(VARCHAR(255), unique=True)
    group: Mapped[Group] = mapped_column(ForeignKey("macrostrat_auth.group.id"))
    used_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


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
    object_group_id: Mapped[int] = mapped_column(
        ForeignKey("storage.object_group.id"), nullable=True
    )
    scheme: Mapped[str] = mapped_column(Enum(SchemeEnum))
    host: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    bucket: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    key: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    source: Mapped[dict] = mapped_column(JSONB, nullable=True)
    mime_type: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    sha256_hash: Mapped[str] = mapped_column(VARCHAR(255), nullable=True)
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    object_group: Mapped["ObjectGroup"] = relationship(back_populates="objects")


class RockdUsageStats(Base):
    __tablename__ = "rockd"
    __table_args__ = {"schema": "usage_stats"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip: Mapped[str] = mapped_column(VARCHAR(45), nullable=False)
    lat: Mapped[float] = mapped_column(nullable=True)
    lng: Mapped[float] = mapped_column(nullable=True)
    matomo_id: Mapped[int] = mapped_column(nullable=True)


class ObjectGroup(Base):
    __tablename__ = "object_group"
    __table_args__ = {"schema": "storage"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Relationships
    objects: Mapped[List["Object"]] = relationship(back_populates="object_group")
    ingest_process: Mapped["IngestProcess"] = relationship(
        back_populates="object_group"
    )


class IngestState(enum.Enum):
    pending = "pending"
    ingested = "ingested"
    prepared = "prepared"
    post_harmonization = "post_harmonization"
    failed = "failed"
    abandoned = "abandoned"


class IngestType(enum.Enum):
    raster = "vector"
    ta1_output = "ta1_output"


class IngestProcess(Base):
    __tablename__ = "ingest_process"
    __table_args__ = {"schema": "maps_metadata"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    state: Mapped[IngestState] = mapped_column(
        ENUM(IngestState, name="ingest_state", schema="maps", native_enum=True),
        nullable=True,
    )

    type: Mapped[str] = mapped_column(
        Enum(IngestType, name="ingest_type"), nullable=True
    )

    comments: Mapped[str] = mapped_column(TEXT, nullable=True)
    map_id: Mapped[str] = mapped_column(TEXT, nullable=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("maps.sources.source_id"), nullable=True
    )
    access_group_id: Mapped[int] = mapped_column(
        ForeignKey("macrostrat_auth.group.id"), nullable=True
    )
    object_group_id: Mapped[ObjectGroup] = mapped_column(
        ForeignKey("storage.object_group.id")
    )
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    object_group: Mapped[ObjectGroup] = relationship(
        back_populates="ingest_process", lazy="joined"
    )
    source: Mapped[Sources] = relationship(back_populates="ingest_process")
    tags: Mapped[List["IngestProcessTag"]] = relationship(
        back_populates="ingest_process", lazy="joined"
    )


class IngestProcessTag(Base):
    __tablename__ = "ingest_process_tag"
    __table_args__ = (
        PrimaryKeyConstraint("ingest_process_id", "tag", name="pk_tag"),
        {"schema": "maps_metadata"},
    )

    ingest_process_id: Mapped[int] = mapped_column(
        ForeignKey("maps_metadata.ingest_process.id")
    )
    tag: Mapped[str] = mapped_column(VARCHAR(255))

    # Relationships
    ingest_process: Mapped[IngestProcess] = relationship(back_populates="tags")
