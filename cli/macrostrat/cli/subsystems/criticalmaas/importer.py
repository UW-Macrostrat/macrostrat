import asyncio
import math
import os
import random
from pathlib import Path

import greenlet
import requests
from criticalmaas.ta1_geopackage import GeopackageDatabase
from geoalchemy2 import Geometry
from sqlalchemy import FLOAT, TEXT, create_engine, insert, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from macrostrat.core.config import PG_DATABASE

INGEST_URL = (
    os.getenv("INGEST_URL") or "https://web.development.svc.macrostrat.org/api/ingest"
)


class Base(DeclarativeBase):
    pass


def SourcePolygonsFactory(base, table_name: str, schema_name: str):
    class SourcePolygons(base):
        __tablename__ = table_name
        __table_args__ = {"schema": schema_name}

        _pkid: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        name_polygon_type: Mapped[str] = mapped_column(TEXT, nullable=False)
        name_geologic_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        color: Mapped[str] = mapped_column(TEXT, nullable=False)
        pattern: Mapped[str] = mapped_column(TEXT, nullable=True)
        abbreviation: Mapped[str] = mapped_column(TEXT, nullable=True)
        description_polygon_type: Mapped[str] = mapped_column(TEXT, nullable=True)
        category: Mapped[str] = mapped_column(TEXT, nullable=True)
        map_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        geometry: Mapped[str] = mapped_column(
            Geometry("MULTIPOLYGON", srid=4326), nullable=False
        )
        type: Mapped[str] = mapped_column(TEXT, nullable=True)
        confidence: Mapped[float] = mapped_column(FLOAT, nullable=True)
        provenance: Mapped[str] = mapped_column(TEXT, nullable=True)
        description_geologic_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        age_text: Mapped[str] = mapped_column(TEXT, nullable=True)
        t_interval: Mapped[str] = mapped_column(TEXT, nullable=True)
        b_interval: Mapped[str] = mapped_column(TEXT, nullable=True)
        t_age: Mapped[float] = mapped_column(FLOAT, nullable=True)
        b_age: Mapped[float] = mapped_column(FLOAT, nullable=True)
        lithology: Mapped[str] = mapped_column(TEXT, nullable=True)
        name: Mapped[str] = mapped_column(TEXT, nullable=True)
        geom: Mapped[str] = mapped_column(
            Geometry("MULTIPOLYGON", srid=4326), nullable=False
        )
        strat_name: Mapped[str] = mapped_column(TEXT, nullable=True)
        age: Mapped[str] = mapped_column(TEXT, nullable=True)
        lith: Mapped[str] = mapped_column(TEXT, nullable=True)
        descrip: Mapped[str] = mapped_column(TEXT, nullable=True)
        comments: Mapped[str] = mapped_column(TEXT, nullable=True)

    return SourcePolygons


async def import_criticalmaas(file: Path):
    """Read a Macrostrat map dataset from a GeoPackage file using GeoPandas and SQLAlchemy."""
    db_url = str(PG_DATABASE)
    # Create the Ingest Process
    ingest_process_data = {"comments": "Ingested from GEOPackage", "state": "pending"}
    ingest_process = requests.post(
        f"{INGEST_URL}/ingest-process", json=ingest_process_data
    ).json()

    filename = str(file.absolute())
    print(f"Importing {filename} into Macrostrat")

    # Add in the sources data
    gpd = GeopackageDatabase(filename)

    # Add in the Sources Table
    map = (
        gpd.run_query(
            "SELECT * FROM map JOIN map_metadata ON map_metadata.map_id = map.id"
        )
        .mappings()
        .all()[0]
    )

    hash = "_temp_" + str(math.floor(random.random() * 100))

    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Add the source row
    async_engine = create_async_engine(db_url)
    async with async_engine.connect() as conn:

        # TODO: Remove the string prefix that prevents id duplication
        source_insert_stmt = text(
            f"INSERT INTO macrostrat.maps.sources (name, primary_table, url, ref_title, authors, ref_year, scale, slug) VALUES ('{map['title']}', '{map['id']}{hash}_polygons', '{map['source_url']}', '{map['title']}', '{map['authors']}', '{map['year']}', '{map['year']}', '{map['id']}{hash}')"
        )
        await conn.execute(source_insert_stmt)
        await conn.commit()

    # Create the polygon table
    polygon_table_name = f"{map['id']}{hash}_polygons"
    polygon_schema_name = "sources"

    SourcePolygons = SourcePolygonsFactory(
        Base, polygon_table_name, polygon_schema_name
    )

    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    # Get the polygon data
    polygon_features = gpd.get_dataframe("polygon_feature")
    polygon_type = gpd.get_dataframe("polygon_type")
    geologic_unit = gpd.get_dataframe("geologic_unit")

    df = polygon_features.merge(
        polygon_type,
        left_on="type",
        right_on="id",
        suffixes=("_polygon_feature", "_polygon_type"),
    ).merge(
        geologic_unit,
        left_on="map_unit",
        right_on="id",
        suffixes=("_polygon_type", "_geologic_unit"),
    )

    # Add in the macrostrat specific columns
    df["geom"] = df["geometry"]
    df["strat_name"] = None
    df["age"] = None
    df["lith"] = df["lithology"]
    df["descrip"] = df["description_polygon_type"]
    df["comments"] = None

    df.drop("id_polygon_feature", axis=1, inplace=True)
    df.drop("id_polygon_type", axis=1, inplace=True)
    df.drop("id", axis=1, inplace=True)
    df.drop("map_id", axis=1, inplace=True)

    # Insert the polygon rows
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        print("Inserting polygons")

        values = [
            {**row, "geom": row["geometry"].wkt, "geometry": row["geometry"].wkt}
            for row in df.to_dict(orient="records")
        ]

        await conn.execute(insert(SourcePolygons), values)
        await conn.commit()


def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
