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
    text,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    BOOLEAN,
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
    license: Mapped[str] = mapped_column(VARCHAR(100))
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


class Role(Base):
    """An application role — `user`, `admin` or `test`.

    Keyed on its own name, so `User.role` is the role itself rather than an
    integer that has to be joined back. `postgres_role` is the Postgres role a
    session in this role assumes; it must match a role created in
    `schema/core/0000-roles.sql`, because it becomes the `role` claim in the
    access JWT and PostgREST applies it verbatim. Callers should still go
    through `api.routes.security.role_claim` rather than reading it directly, so
    an unknown mapping falls back rather than producing an unusable claim.
    """

    __tablename__ = "role"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[str] = mapped_column(TEXT, primary_key=True)
    postgres_role: Mapped[str] = mapped_column(TEXT)
    description: Mapped[str] = mapped_column(TEXT, nullable=True)
    users: Mapped[List["User"]] = relationship(back_populates="role_definition")


class User(Base):
    __tablename__ = "user"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub: Mapped[str] = mapped_column(TEXT, unique=True)
    name: Mapped[str] = mapped_column(TEXT, nullable=True)
    display_name: Mapped[str] = mapped_column(TEXT, nullable=True)
    email: Mapped[str] = mapped_column(TEXT, nullable=True)
    # The role *name* is the foreign key, so `user.role == "admin"` is the check —
    # no join, no id to resolve. `role_definition` is the row behind it, needed
    # only when the Postgres-role mapping matters.
    role: Mapped[str] = mapped_column(ForeignKey("macrostrat_auth.role.id"))
    role_definition: Mapped[Role] = relationship(lazy="joined", back_populates="users")
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Token(Base):
    """An issued API token.

    `token` holds the sha256 hex digest of the token, never the token itself.
    A token either delegates a Macrostrat user's authority (`user_id`) or
    belongs to a third party with no account, in which case `label` carries the
    identity and `created_by` records the admin who issued it.
    """

    __tablename__ = "token"
    __table_args__ = {"schema": "macrostrat_auth"}
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(TEXT, unique=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("macrostrat_auth.user.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("macrostrat_auth.user.id"), nullable=True
    )
    token_type: Mapped[str] = mapped_column(
        TEXT,
        nullable=False,
        server_default=text("'api'"),
    )
    label: Mapped[str] = mapped_column(TEXT, nullable=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(TEXT), nullable=True)
    used_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_on: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(lazy="joined", foreign_keys=[user_id])


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

    # An ingest process is 1:1 with a map source, so source_id is the primary
    # key — there is no separate surrogate `id`.
    source_id: Mapped[int] = mapped_column(
        ForeignKey("maps.sources.source_id"), primary_key=True
    )

    # Plain text with an FK to maps_metadata.ingest_state, so that lookup table
    # owns the allowed values and they can change without a code change. The
    # IngestState enum is kept for reference but is not bound to this column.
    state: Mapped[str] = mapped_column(TEXT, nullable=True)

    # DIVERGENT — `type`, `map_id` and `access_group_id` are not columns on
    # maps_metadata.ingest_process, so any query selecting them fails with
    # "column does not exist". Commented out until they are either added to the
    # table or dropped from the model for good.
    # type: Mapped[str] = mapped_column(
    #     Enum(IngestType, name="ingest_type"), nullable=True
    # )

    comments: Mapped[str] = mapped_column(TEXT, nullable=True)
    # map_id: Mapped[str] = mapped_column(TEXT, nullable=True)
    # access_group_id — note that `macrostrat_auth.group` no longer exists; if
    # per-map access control is revived it belongs against organizations, not
    # the role table that replaced it.
    # access_group_id: Mapped[int] = mapped_column(nullable=True)

    created_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_on: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    source: Mapped[Sources] = relationship(back_populates="ingest_process")
    tags: Mapped[List["IngestProcessTag"]] = relationship(
        back_populates="ingest_process", lazy="joined"
    )


class MapFiles(Base):
    __tablename__ = "map_files"
    __table_args__ = {"schema": "maps_metadata"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # A map can have many files, so source_id is a plain foreign key here.
    source_id: Mapped[int] = mapped_column(
        ForeignKey("maps_metadata.ingest_process.source_id", ondelete="CASCADE"),
        nullable=False,
    )

    object_id: Mapped[int] = mapped_column(
        ForeignKey("storage.object.id", ondelete="CASCADE"),
        nullable=False,
    )


class IngestProcessTag(Base):
    __tablename__ = "ingest_process_tag"
    __table_args__ = (
        PrimaryKeyConstraint("source_id", "tag", name="pk_tag"),
        {"schema": "maps_metadata"},
    )

    source_id: Mapped[int] = mapped_column(
        ForeignKey("maps_metadata.ingest_process.source_id")
    )
    tag: Mapped[str] = mapped_column(VARCHAR(255))

    # Relationships
    ingest_process: Mapped[IngestProcess] = relationship(back_populates="tags")
