import asyncio
import os
import random
import math
import datetime

import minio
import requests
from sqlalchemy import create_engine, TEXT, text, FLOAT, insert, INTEGER, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, async_sessionmaker
from geoalchemy2 import Geometry, functions
import greenlet

import geopandas as g
from geoalchemy2 import Geometry

from criticalmaas.ta1_geopackage import GeopackageDatabase

import dotenv
dotenv.load_dotenv()

INGEST_URL = os.getenv("INGEST_URL") or "https://web.development.svc.macrostrat.org/api/ingest"


def get_async_engine():
    db_url = os.environ["uri"]
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(db_url)

class Base(DeclarativeBase):
    pass


def SourcePolygonsFactory(base, table_name: str, schema_name: str):
    class SourcePolygons(base):
        __tablename__ = table_name
        __table_args__ = {'schema': schema_name}

        _pkid: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        source_id: Mapped[int] = mapped_column(INTEGER)
        name_polygon_type: Mapped[str] = mapped_column(TEXT, nullable=True)
        name_geologic_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        color: Mapped[str] = mapped_column(TEXT, nullable=True)
        pattern: Mapped[str] = mapped_column(TEXT, nullable=True)
        abbreviation: Mapped[str] = mapped_column(TEXT, nullable=True)
        description_polygon_type: Mapped[str] = mapped_column(TEXT, nullable=True)
        category: Mapped[str] = mapped_column(TEXT, nullable=True)
        map_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        geometry: Mapped[str] = mapped_column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)
        type: Mapped[str] = mapped_column(TEXT, nullable=True)
        confidence: Mapped[float] = mapped_column(FLOAT, nullable=True)
        provenance: Mapped[str] = mapped_column(TEXT, nullable=True)
        description_geologic_unit: Mapped[str] = mapped_column(TEXT, nullable=True)
        age_text: Mapped[str] = mapped_column(TEXT, nullable=True)
        input_t_interval: Mapped[int] = mapped_column(TEXT, nullable=True)
        input_b_interval: Mapped[int] = mapped_column(TEXT, nullable=True)
        t_age: Mapped[float] = mapped_column(FLOAT, nullable=True)
        b_age: Mapped[float] = mapped_column(FLOAT, nullable=True)
        lithology: Mapped[str] = mapped_column(TEXT, nullable=True)
        name: Mapped[str] = mapped_column(TEXT, nullable=True)
        geom: Mapped[str] = mapped_column(Geometry('MULTIPOLYGON', srid=4326), nullable=False)
        strat_name: Mapped[str] = mapped_column(TEXT, nullable=True)
        age: Mapped[str] = mapped_column(TEXT, nullable=True)
        lith: Mapped[str] = mapped_column(TEXT, nullable=True)
        descrip: Mapped[str] = mapped_column(TEXT, nullable=True)
        comments: Mapped[str] = mapped_column(TEXT, nullable=True)
        t_interval: Mapped[str] = mapped_column(INTEGER, nullable=True)
        b_interval: Mapped[str] = mapped_column(INTEGER, nullable=True)

    return SourcePolygons


def SourceLineFactory(base, table_name: str, schema_name: str):

    class SourceLine(base):
        __tablename__ = table_name
        __table_args__ = {'schema': schema_name}

        _pkid: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        source_id: Mapped[int] = mapped_column(INTEGER)

        polarity: Mapped[int] = mapped_column(INTEGER, nullable=True)
        provenance: Mapped[str] = mapped_column(TEXT, nullable=True)
        type: Mapped[str] = mapped_column(TEXT, nullable=True)
        confidence: Mapped[float] = mapped_column(FLOAT, nullable=True)
        geometry: Mapped[str] = mapped_column(Geometry('MULTILINESTRING', srid=4326), nullable=False)
        name: Mapped[str] = mapped_column(TEXT, nullable=True)
        dash_pattern: Mapped[str] = mapped_column(TEXT, nullable=True)
        description: Mapped[str] = mapped_column(TEXT, nullable=True)
        symbol: Mapped[str] = mapped_column(TEXT, nullable=True)

    return SourceLine


def SourcePointFactory(base, table_name: str, schema_name: str):

    class SourcePoint(base):
        __tablename__ = table_name
        __table_args__ = {'schema': schema_name}

        # For Macrostrat
        _pkid: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        source_id: Mapped[int] = mapped_column(INTEGER)

        # From the point feature
        provenance: Mapped[str] = mapped_column(TEXT, nullable=True)
        type: Mapped[str] = mapped_column(TEXT, nullable=True)
        confidence: Mapped[float] = mapped_column(FLOAT, nullable=True)
        dip: Mapped[float] = mapped_column(FLOAT, nullable=True)
        dip_direction: Mapped[float] = mapped_column(FLOAT, nullable=True)
        geometry: Mapped[str] = mapped_column(Geometry('MULTIPOINT', srid=4326), nullable=False)

        # From the point type
        name: Mapped[str] = mapped_column(TEXT, nullable=True)
        description: Mapped[str] = mapped_column(TEXT, nullable=True)

    return SourcePoint


def get_gpkg(object: str, filename: str = "temp.gpkg"):
    client = minio.Minio(
        "storage.macrostrat.org",
        access_key=os.getenv("access_key"),
        secret_key=os.getenv("secret_key"),
        secure=True
    )

    try:
        response = client.get_object("map-inbox", object)

        # Read data from response.
        with open(filename, "wb") as file_data:
            for d in response.stream(32*1024):
                file_data.write(d)

    finally:
        response.close()
        response.release_conn()

    return True


async def import_polygons(gpd: GeopackageDatabase, map_name: str, source_id: int, async_engine: AsyncEngine):
    """Import polygons into macrostrat from a GeoPackageDatabase"""

    # Create the polygon table
    polygon_table_name = f"{map_name}_polygons"
    polygon_schema_name = "sources"

    SourcePolygons = SourcePolygonsFactory(Base, polygon_table_name, polygon_schema_name)

    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    # Get the polygon data
    polygon_features = gpd.get_dataframe("polygon_feature")
    polygon_type = g.GeoDataFrame(gpd.run_query("SELECT * FROM polygon_type").mappings().all())
    geologic_unit = g.GeoDataFrame(gpd.run_query("SELECT * FROM geologic_unit").mappings().all())

    df = polygon_features
    if len(polygon_type) > 0:
        df = polygon_features.merge(polygon_type, left_on="type", right_on="id", suffixes=("_polygon_feature", "_polygon_type"))

        if len(geologic_unit) > 0:
            df = df.merge(geologic_unit, left_on="map_unit", right_on="id", suffixes=("_polygon_type", "_geologic_unit"))

    # Add in the macrostrat specific columns
    df['source_id'] = source_id
    df['geom'] = df['geometry'] if 'geometry' in df.columns else None
    df['strat_name'] = None
    df['age'] = None
    df['lith'] = df['lithology'] if 'lithology' in df.columns else None
    df['descrip'] = df['description_polygon_type'] if 'description_polygon_type' in df.columns else None
    df['comments'] = None
    df['input_t_interval'] = df['t_interval'] if 't_interval' in df.columns else None
    df['input_b_interval'] = df['b_interval'] if 'b_interval' in df.columns else None
    df['t_interval'] = None
    df['b_interval'] = None

    if "id_polygon_feature" in df.columns:
        df.drop("id_polygon_feature", axis=1, inplace=True)

    if "id_polygon_type" in df.columns:
        df.drop("id_polygon_type", axis=1, inplace=True)

    if "id" in df.columns:
        df.drop("id", axis=1, inplace=True)

    if "map_id" in df.columns:
        df.drop("map_id", axis=1, inplace=True)


    # Insert the polygon rows
    async with async_engine.connect() as conn:

        values = [{**row, "geom": row['geometry'].wkt, "geometry": row['geometry'].wkt} for row in df.to_dict(orient="records")]

        if len(values) > 0:
            await conn.execute(
                insert(SourcePolygons),
                values
            )
            await conn.commit()


async def import_lines(gpd: GeopackageDatabase, map_name: str, source_id: int, async_engine: AsyncEngine):
    """Import the line data from the ta1_geopackage"""

    # Create the line table
    line_table_name = f"{map_name}_lines"
    line_schema_name = "sources"

    SourceLines = SourceLineFactory(Base, line_table_name, line_schema_name)
    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    # Get the line data
    line_features = gpd.get_dataframe("line_feature")
    line_type = g.GeoDataFrame(gpd.run_query("SELECT * FROM line_type").mappings().all())

    df = line_features
    if len(line_type) > 0:
        df = line_features.merge(line_type, left_on="type", right_on="id", suffixes=("_feature", "_type"))

    # Add in the macrostrat specific columns
    df['source_id'] = source_id
    df['geom'] = df['geometry'] if 'geometry' in df.columns else None

    # Insert the line rows
    async with async_engine.connect() as conn:

        values = [{**row, "geom": row['geometry'].wkt, "geometry": row['geometry'].wkt} for row in df.to_dict(orient="records")]

        if len(values) > 0:
            await conn.execute(
                insert(SourceLines),
                values
            )
            await conn.commit()


async def import_points(gpd: GeopackageDatabase, map_name: str, source_id: int, async_engine: AsyncEngine):
    """Import the point data from the ta1_geopackage"""

    # Create the point table
    point_table_name = f"{map_name}_points"
    point_schema_name = "sources"

    SourcePoints = SourcePointFactory(Base, point_table_name, point_schema_name)
    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    # Get the point data
    point_features = gpd.get_dataframe("point_feature")
    point_type = g.GeoDataFrame(gpd.run_query("SELECT * FROM point_type").mappings().all())

    df = point_features
    if len(point_type) > 0:
        df = point_features.merge(point_type, left_on="type", right_on="id", suffixes=("_feature", "_type"))

    # Add in the macrostrat specific columns
    df['source_id'] = source_id
    df['geom'] = df['geometry'] if 'geometry' in df.columns else None

    # Insert the point rows
    async with async_engine.connect() as conn:

        values = [{**row, "geom": row['geometry'].wkt, "geometry": row['geometry'].wkt} for row in df.to_dict(orient="records")]

        if len(values) > 0:
            await conn.execute(
                insert(SourcePoints),
                values
            )
            await conn.commit()


async def import_geopackage_map(object: str, map_name: str = None):
    """Read a Macrostrat map dataset from a GeoPackage file using GeoPandas and SQLAlchemy."""

    async_engine = get_async_engine()

    # Get the file
    TEMP_FILE = "temp.gpkg"
    get_gpkg(object, TEMP_FILE)

    # Open the file as a GeoPackageDB
    gpd = GeopackageDatabase(TEMP_FILE)

    # Add the map to the sources table
    map = gpd.run_query("SELECT * FROM map LEFT JOIN map_metadata ON map_metadata.map_id = map.id").mappings().all()[0]

    # Check for overrides and awkward missing values
    map_title = map['title'] if map['title'] is not None else map_name

    async with async_engine.connect() as conn:
        source_insert_stmt = text(
            f"INSERT INTO macrostrat.maps.sources (name, primary_table, url, ref_title, authors, ref_year, scale, slug) VALUES ('{map_title}', '{map_name}_polygons', '{map['source_url']}', '{map_title}', '{map['authors']}', '{map['year']}', '{map['year']}', '{map_name}') RETURNING source_id")
        source_id = (await conn.execute(source_insert_stmt)).all()[0][0]

        await conn.commit()

    # Create the Ingest Process
    ingest_process_data = {
      "comments": f"Ingested from GEOPackage {source_id}",
      "state": "pending",
      "source_id": source_id
    }
    ingest_process_response = requests.post(f"{INGEST_URL}/ingest-process", json=ingest_process_data)
    ingest_process = ingest_process_response.json()

    # Ingest the Polygons
    await import_polygons(gpd, map_name, source_id, async_engine)
    await import_lines(gpd, map_name, source_id, async_engine)
    await import_points(gpd, map_name, source_id, async_engine)

    # Update the ingest process to indicate ingested
    ingest_process_data = {
      "state": "ingested"
    }
    ingest_process_response = requests.patch(f"{INGEST_URL}/ingest-process/{ingest_process['id']}", json=ingest_process_data)
    assert ingest_process_response.status_code == 200


async def auto_ingest(object):
    name = "umn_usc_inferlink" + "_" + object.split("/")[-1].split(".")[0] + "_" + "v4"
    await import_geopackage_map(object, name)


async def ingest_s2_ls_output(objects: str):

    objects = [x.split()[3] for x in objects.split("\n")]

    for object in objects:
        await auto_ingest(object)


async def main():

    f = """2024-02-15 18:11:16  143720448 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/169_34067.gpkg
2024-02-15 18:11:47    9457664 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/17977_9267.gpkg
2024-02-15 18:11:27   63987712 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/2188_1086.gpkg
2024-02-15 18:12:05   40390656 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/22253_25695.gpkg
2024-02-15 18:11:02   46219264 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/261_9030.gpkg
2024-02-15 18:11:01  170156032 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/2639_10957.gpkg
2024-02-15 18:12:01   96743424 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/2647_10991.gpkg
2024-02-15 18:11:48     344064 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/31361_19154.gpkg
2024-02-15 18:11:49  241238016 umn-usc-inferlink/hackathon_6mth_results/geo_coord_gpkg/v4/7064_9296.gpkg"""

    await ingest_s2_ls_output(f)

if __name__ == "__main__":
    asyncio.run(main())
