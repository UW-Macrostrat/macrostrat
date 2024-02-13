import asyncio
import os
import random
import math

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
import greenlet

import geopandas as g
from geoalchemy2 import Geometry

from criticalmaas.ta1_geopackage import GeopackageDatabase

import dotenv
dotenv.load_dotenv()

INGEST_URL = os.getenv("INGEST_URL") or "https://web.development.svc.macrostrat.org/api/ingest"

def import_geopackage_map(filename: str):
    """Read a Macrostrat map dataset from a GeoPackage file using GeoPandas and SQLAlchemy."""

    # Create the Ingest Process
    ingest_process_data = {
      "comments": "Ingested from GEOPackage",
      "state": "pending"
    }
    ingest_process = requests.post(f"{INGEST_URL}/ingest-process", json=ingest_process_data).json()

    # Add in the sources data
    gpd = GeopackageDatabase(filename)

    # Add in the Sources Table
    map = gpd.run_query("SELECT * FROM map JOIN map_metadata ON map_metadata.map_id = map.id").mappings().all()[0]

    hash = "_temp_" + str(math.floor(random.random() * 100))

    engine = create_engine(os.getenv("uri"))
    with engine.connect() as conn:

        # TODO: Remove the string prefix that prevents id duplication
        source_insert_stmt = text(f"INSERT INTO macrostrat.maps.sources (name, primary_table, url, ref_title, authors, ref_year, scale, slug) VALUES ('{map['title']}', '{map['id']}{hash}_polygons', '{map['source_url']}', '{map['title']}', '{map['authors']}', '{map['year']}', '{map['year']}', '{map['id']}{hash}')")
        conn.execute(source_insert_stmt)

        conn.commit()

    # Add in the Polygon Table
    polygon_features = gpd.get_dataframe("polygon_feature")
    polygon_type = gpd.get_dataframe("polygon_type")
    geologic_unit = gpd.get_dataframe("geologic_unit")

    df = polygon_features.merge(polygon_type, left_on="type", right_on="id", suffixes=("_polygon_feature", "_polygon_type")).merge(geologic_unit, left_on="map_unit", right_on="id", suffixes=("_polygon_type", "_geologic_unit"))

    # Add in the macrostrat specific comments
    df['geom'] = df['geometry']
    df['strat_name'] = None
    df['age'] = None
    df['lith'] = df['lithology']
    df['descrip'] = df['description_polygon_type']
    df['comments'] = None

    df.drop("id_polygon_feature", axis=1, inplace=True)
    df.drop("id_polygon_type", axis=1, inplace=True)
    df.drop("id", axis=1, inplace=True)
    df.drop("map_id", axis=1, inplace=True)

    # Create the polygon table
    polygon_table_name = f"{map['id']}{hash}_polygons"
    polygon_schema_name = "macrostrat.sources"
    polygon_full_table_name = f"{polygon_schema_name}.{polygon_table_name}"
    with engine.connect() as conn:
        table_creation_query = text(f"""
        CREATE TABLE {polygon_full_table_name} (
            name_polygon_type TEXT NOT NULL, -- name of the polygon type
            name_geologic_unit TEXT,
            color TEXT NOT NULL , -- color extracted from map/legend
            pattern TEXT, -- pattern extracted from map/legend
            abbreviation TEXT, -- abbreviation extracted from map/legend
            description_polygon_type TEXT, -- description text extracted from legend
            category TEXT, -- name of containing legend block
            map_unit TEXT, -- map unit information
            geometry geometry(MultiPolygon,4326) NOT NULL, -- polygon geometry, world coordinates
            type TEXT, -- polygon type information
            confidence REAL, -- confidence associated with this extraction
            provenance TEXT, -- provenance for this extraction
            description_geologic_unit TEXT, -- description of the geologic unit
            age_text TEXT, -- age of the geologic unit, textual description
            t_interval TEXT, -- geologic time interval, youngest
            b_interval TEXT, -- geologic time interval, oldest
            t_age REAL, -- Minimum age (Ma)
            b_age REAL, -- Maximum age (Ma)
            lithology TEXT, -- comma-separated array of lithology descriptors extracted from legend text
            name TEXT,
            geom geometry(MultiPolygon,4326),
            strat_name TEXT,
            age TEXT, 
            lith TEXT, 
            descrip TEXT,
            comments TEXT
        );
        """)
        conn.execute(table_creation_query)
        conn.commit()

    db_url = os.environ["uri"]
    if db_url.startswith("postgresql://") and False:
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_engine(db_url)
    conn = engine.raw_connection()

    # Populate the polygon table from the geopanda
    df.to_postgis(
        polygon_table_name,
        engine.connect(),
        schema="sources",
        if_exists="append"
        # dtype={
        #     "geometry": Geometry(
        #         geometry_type="Geometry",
        #         spatial_index=True,
        #         srid=4326,
        #     ),
        # }
    )

def chunker(seq, size):
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))


def main():
    response = import_geopackage_map("/Users/clock/PycharmProjects/macrostrat-cli/cli/macrostrat/cli/io/criticalmaas/test/data/bc_kananaskis.gpkg")


if __name__ == "__main__":
    main()
