CREATE FUNCTION tile_layers.fossils(x integer, y integer, z integer, filter json) returns bytea
  immutable
  strict
  language plpgsql
as $$
DECLARE
  mercator_bbox geometry;
  projected_bbox geometry;
  tile_data bytea;
BEGIN
  mercator_bbox := ST_TileEnvelope(z, x, y);

  projected_bbox := ST_Transform(mercator_bbox, 4326);

  -- Select and prepare geometries as MVT features
  WITH tile AS (
    SELECT
      collection_no,
      name,
      ST_AsMVTGeom(
        ST_Transform(geom, 3857),
        mercator_bbox,
        4096,
        256,
        true
      ) AS geom
    FROM macrostrat.pbdb_collections
    WHERE ST_Intersects(geom, projected_bbox)
  ),

       mvt_features as (
         select collection_no, ST_SnapToGrid(geom, 256, 256) as cluster_geom, geom from tile),
       grouped_features as (SELECT
                              tile_utils.cluster_expansion_zoom(ST_Collect(geom),z) as expansion_zoom,
                              count(*) AS n,
                              st_centroid(ST_Collect(geom)) as geom,
                              CASE
                                WHEN count(*) < 2 THEN string_agg(f.collection_no::text, ',')
                                ELSE null
                                END AS collection_no
                            FROM mvt_features f
                            GROUP BY cluster_geom)
  SELECT ST_AsMVT(row) as mvt
  FROM (SELECT * FROM grouped_features) as row
  INTO tile_data;

  RETURN tile_data;
END;
$$;

alter function tile_layers.fossils(integer, integer, integer, json) owner to macrostrat_admin;
