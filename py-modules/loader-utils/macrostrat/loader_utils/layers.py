"""Load one geospatial layer into a table, inferring its structure.

Reading is done with pyogrio, a direct GDAL/OGR binding, so this handles the
formats `ogr2ogr` does (Shapefile, GeoPackage, GeoJSON, FileGDB, KML, …) without
shelling out to it or putting database credentials on a command line. Attributes
go through the same type inference and `COPY` path as tabular loads; geometry
travels as hex EWKB.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import polars as pl
from psycopg.sql import Identifier
from sqlalchemy.engine import Engine

from macrostrat.database.utils import run_sql
from macrostrat.utils import get_logger

from .tables import (
    LoadError,
    check_target,
    comment_original_names,
    copy_dataframe,
    create_table,
    dedupe,
    identifier,
    pg_type,
    polars_from_pandas,
)

log = get_logger(__name__)

# Macrostrat stores geometry in WGS84 unless told otherwise
DEFAULT_SRID = 4326

# OGR geometry type names -> PostGIS typmod names. Anything absent (or mixed
# within a layer) falls back to the unconstrained 'Geometry'.
_GEOM_TYPES = {
    "Point": "Point",
    "LineString": "LineString",
    "Polygon": "Polygon",
    "MultiPoint": "MultiPoint",
    "MultiLineString": "MultiLineString",
    "MultiPolygon": "MultiPolygon",
    "GeometryCollection": "GeometryCollection",
    "LinearRing": "LineString",
}

_PROMOTE_TO_MULTI = {
    "Point": "MultiPoint",
    "LineString": "MultiLineString",
    "Polygon": "MultiPolygon",
}


@dataclass
class LoadedLayer:
    """What a layer load created, or would create on a dry run."""

    schema: str
    table: str
    columns: list[str]
    types: list[str]
    # None for an attribute-only layer
    geometry_type: Optional[str]
    srid: Optional[int]
    features: int
    # None on a dry run
    copied: Optional[int] = None


def load_layer(
    engine: Engine,
    file: Path | str,
    layer: str,
    *,
    schema: str = "temp",
    table: Optional[str] = None,
    single_layer: bool = True,
    srid: Optional[int] = None,
    keep_srid: bool = False,
    source_srid: Optional[int] = None,
    geometry_column: str = "geom",
    fid_column: Optional[str] = None,
    promote_to_multi: bool = False,
    index: bool = True,
    where: Optional[str] = None,
    replace: bool = False,
    append: bool = False,
    dry_run: bool = False,
) -> LoadedLayer:
    """Load `layer` of `file` into `schema.table`, creating the table to match.

    `table` defaults to a name built from the file and layer. `fid_column` keeps
    the layer's feature ID as an attribute, which formats such as GeoPackage
    otherwise hold apart from the attributes. `file` may be a GDAL virtual path
    (`/vsizip/…`).

    Each statement runs and commits on its own connection, so a caller whose open
    transaction has read `table` must commit first, or a replace will wait on it.
    """
    import geopandas as gpd

    if replace and append:
        raise LoadError("replace and append are mutually exclusive")
    if keep_srid and srid is not None:
        raise LoadError(
            "keep_srid and srid are mutually exclusive: one keeps the file's CRS, "
            "the other reprojects away from it"
        )

    if table is None:
        table = layer_table_name(file, layer, single_layer=single_layer)
    label = f"{file}:{layer}"

    gdf = gpd.read_file(
        file,
        layer=layer,
        engine="pyogrio",
        where=where,
        fid_as_index=fid_column is not None,
    )
    if fid_column is not None:
        gdf = gdf.reset_index(names=fid_column)

    # Attribute-only layers (lookup tables in a GeoPackage) come back as plain frames.
    spatial = isinstance(gdf, gpd.GeoDataFrame)
    geom_type = srid_out = None
    if spatial:
        if gdf.geometry.isna().all():
            log.warning("Layer %s has no usable geometry", label)
        gdf, srid_out = _resolve_crs(
            gdf, srid=srid, keep_srid=keep_srid, source_srid=source_srid, label=label
        )
        if promote_to_multi:
            gdf = _promote(gdf)
        geom_type = _geometry_type(gdf, promote_to_multi=promote_to_multi)

    # Split geometry off, then run the attributes through the tabular path.
    attr_frame = gdf.drop(columns=[gdf.geometry.name]) if spatial else gdf
    source_columns = list(attr_frame.columns)
    attrs = _restore_integers(polars_from_pandas(attr_frame), file, layer)
    columns = dedupe([identifier(c) for c in source_columns])
    attrs.columns = columns
    types = [pg_type(dtype) for dtype in attrs.schema.values()]

    all_columns, declared, created = columns, types, types
    if spatial:
        geom_col = identifier(geometry_column, fallback="geom")
        if geom_col in columns:
            raise LoadError(
                f"Attribute column '{geom_col}' of {label} collides with the "
                "geometry column; choose another geometry column name"
            )
        all_columns = columns + [geom_col]
        declared = types + [f"geometry({geom_type}, {srid_out})"]
        # Untyped until after the COPY: hex WKB carries no SRID, so a typed
        # column would fail its SRID check on insert.
        created = types + ["geometry"]

    result = LoadedLayer(
        schema=schema,
        table=table,
        columns=all_columns,
        types=declared,
        geometry_type=geom_type,
        srid=srid_out,
        features=len(gdf),
    )
    if dry_run:
        return result

    check_target(engine, schema, table, replace=replace, append=append)

    if not append:
        create_table(engine, schema, table, all_columns, created, replace=replace)
        comment_original_names(engine, schema, table, source_columns, columns)

    if spatial:
        # A plain list avoids pyarrow, and normalizes the float NaN that to_wkb
        # reports for a missing geometry.
        wkb = [v if isinstance(v, str) else None for v in gdf.geometry.to_wkb(hex=True)]
        attrs = attrs.with_columns(pl.Series(geom_col, wkb, dtype=pl.String))

    result.copied = copy_dataframe(engine, attrs, schema, table, all_columns)

    if spatial and not append:
        _apply_srid(engine, schema, table, geom_col, geom_type, srid_out)
        if index:
            _create_index(engine, schema, table, geom_col)

    return result


_INTEGERS = {
    "int8": pl.Int8,
    "int16": pl.Int16,
    "int32": pl.Int32,
    "int64": pl.Int64,
    "uint8": pl.UInt8,
    "uint16": pl.UInt16,
    "uint32": pl.UInt32,
    "uint64": pl.UInt64,
}


def _restore_integers(attrs: pl.DataFrame, file, layer: str) -> pl.DataFrame:
    """Cast back integer fields that pandas widened to float to hold nulls."""
    from pyogrio import read_info

    info = read_info(file, layer=layer)
    declared = dict(zip(info["fields"], info["dtypes"]))
    casts = [
        pl.col(name).cast(_INTEGERS[str(declared[name])])
        for name, dtype in attrs.schema.items()
        if dtype.is_float() and str(declared.get(name)) in _INTEGERS
    ]
    return attrs.with_columns(casts) if casts else attrs


def layer_table_name(file: Path | str, layer: str, *, single_layer: bool) -> str:
    """Name the table after the file, disambiguating by layer when needed"""
    stem = identifier(Path(file).name.split(".")[0], fallback="table")
    layer_name = identifier(layer, fallback="layer")
    # A single-layer file usually names its layer after itself; don't stutter
    if single_layer or layer_name == stem:
        return stem
    return f"{stem}_{layer_name}"[:63]


def _resolve_crs(
    gdf,
    *,
    srid: Optional[int],
    keep_srid: bool,
    source_srid: Optional[int],
    label: str,
):
    """Settle the layer's CRS, reprojecting unless asked to keep it.

    Returns the frame together with the SRID its geometry is actually in, which
    is what the geometry column gets declared as.
    """
    if gdf.crs is None:
        if keep_srid and source_srid is None:
            raise LoadError(
                f"{label} has no CRS of its own to keep; declare a source SRID"
            )
        assumed = source_srid or srid or DEFAULT_SRID
        log.warning("%s has no CRS; assuming EPSG:%s", label, assumed)
        gdf = gdf.set_crs(epsg=assumed)
    elif source_srid is not None:
        gdf = gdf.set_crs(epsg=source_srid, allow_override=True)

    current = gdf.crs.to_epsg()

    if keep_srid:
        if current is None:
            raise LoadError(
                f"{label} has a CRS with no EPSG code, so it cannot be stored as a "
                "PostGIS SRID; reproject it, or declare the equivalent source SRID"
            )
        return gdf, current

    target = srid or DEFAULT_SRID
    if current != target:
        log.info("Reprojecting %s from EPSG:%s to EPSG:%s", label, current, target)
        gdf = gdf.to_crs(epsg=target)
    return gdf, target


def _promote(gdf):
    """Promote single geometries to their Multi* equivalent"""
    from shapely.geometry import MultiLineString, MultiPoint, MultiPolygon

    wrappers = {
        "Point": MultiPoint,
        "LineString": MultiLineString,
        "Polygon": MultiPolygon,
    }

    def _wrap(geom):
        if geom is None:
            return None
        wrapper = wrappers.get(geom.geom_type)
        return wrapper([geom]) if wrapper else geom

    return gdf.set_geometry(gdf.geometry.map(_wrap), crs=gdf.crs)


def _geometry_type(gdf, *, promote_to_multi: bool) -> str:
    """Pick the narrowest PostGIS type that covers every feature in the layer"""
    present = {t for t in gdf.geom_type.dropna().unique()}
    if not present:
        return "Geometry"

    mapped = set()
    for t in present:
        name = _GEOM_TYPES.get(t)
        if name is None:
            return "Geometry"
        if promote_to_multi:
            name = _PROMOTE_TO_MULTI.get(name, name)
        mapped.add(name)

    if len(mapped) != 1:
        return "Geometry"

    geom_type = mapped.pop()
    # Preserve a Z dimension if every geometry carries one
    has_z = gdf.geometry.dropna().has_z
    if len(has_z) and bool(has_z.all()):
        geom_type += "Z"
    return geom_type


def _apply_srid(
    engine: Engine, schema: str, table: str, column: str, geom_type: str, srid: int
):
    """Constrain the geometry column and stamp the SRID onto its contents"""
    run_sql(
        engine,
        "ALTER TABLE {table} ALTER COLUMN {column} "
        "TYPE geometry(" + geom_type + ", " + str(srid) + ") "
        "USING ST_SetSRID({column}, " + str(srid) + ")",
        dict(
            table=Identifier(schema, table),
            column=Identifier(column),
        ),
        raise_errors=True,
    )


def _create_index(engine: Engine, schema: str, table: str, column: str):
    index = identifier(f"{table}_{column}_idx")
    run_sql(
        engine,
        "CREATE INDEX {index} ON {table} USING GIST ({column})",
        dict(
            index=Identifier(index),
            table=Identifier(schema, table),
            column=Identifier(column),
        ),
        raise_errors=True,
    )
