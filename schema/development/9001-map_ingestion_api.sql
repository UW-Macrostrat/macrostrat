CREATE SCHEMA IF NOT EXISTS map_ingestion_api;

CREATE OR REPLACE FUNCTION map_ingestion_api.collect_unique_values(state text[], next_val anyelement)
  RETURNS text[] AS $$
BEGIN
  IF next_val IS NULL THEN
    RETURN state;
  END IF;
  IF state IS NULL THEN
    RETURN ARRAY[next_val::text];
  END IF;
  IF next_val = ANY(state) THEN
    RETURN state;
  END IF;
  RETURN state || ARRAY[next_val::text];
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION map_ingestion_api.aggregate_if_small(state anyarray)
  RETURNS jsonb AS $$
BEGIN
  -- Return json if multiple values are present
  IF array_length(state, 1) > 3 THEN
    RETURN '"Multiple"'::jsonb;
  END IF;
  IF array_length(state, 1) = 0 THEN
    RETURN null::jsonb;
  END IF;
  IF array_length(state, 1) = 1 THEN
    RETURN to_jsonb(state[1]);
  END IF;
  RETURN to_jsonb(state);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE AGGREGATE map_ingestion_api.build_groups(text) (
  SFUNC = map_ingestion_api.collect_unique_values,
  STYPE = text[],
  FINALFUNC = map_ingestion_api.aggregate_if_small,
  INITCOND = '{}'
  );

CREATE OR REPLACE FUNCTION map_ingestion_api.grouped_query(_table_name text, _group_by_columns text[]) returns TABLE(result jsonb, oid bigint)
  language plpgsql
as $$
DECLARE
  all_columns   TEXT[];
  agg_columns   TEXT[];
  group_by_list TEXT;
  agg_select    TEXT;
  query         TEXT;
BEGIN
  -- Get all columns from the specified table
  SELECT array_agg(column_name::TEXT)
  INTO all_columns
  FROM information_schema.columns
  WHERE table_schema || '.' || table_name = _table_name
     OR table_name = _table_name;

  -- Get columns to aggregate (exclude group by columns)
  SELECT array_agg(col)
  INTO agg_columns
  FROM unnest(all_columns) AS col
  WHERE col != any(_group_by_columns)
    AND col != 'geom'
    AND col != 'geometry';

  -- Build GROUP BY clause
  group_by_list := array_to_string(_group_by_columns, ', ');

  -- Build aggregation SELECT with array_agg for each non-group column
  SELECT string_agg(
    format('map_ingestion_api.build_groups(%I::text) AS %I', col, col),
    ', '
         )
  INTO agg_select
  FROM unnest(agg_columns) AS col;

  -- Build and execute dynamic query
  query := format(
    'SELECT row_to_json(t)::JSONB FROM (SELECT %s, %s FROM %s GROUP BY %s) t',
    group_by_list,
    agg_select,
    _table_name,
    group_by_list
           );

  RETURN QUERY EXECUTE query;
END;
$$;

SELECT * FROM map_ingestion_api.grouped_query('sources.namibia_250k_polygons', ARRAY['lithcode']) LIMIT 2;
