DO $$
DECLARE
    table_name text;
    source_schema text := 'macrostrat';
    target_schema text := 'macrostrat_temp';
    tables text[] := ARRAY[
        'strat_name_footprints',
        'grainsize',
        'pbdb_collections',
        'pbdb_collections_strat_names',
        'temp_rocks',
        'temp_names',
        'unit_lith_atts'
    ];
BEGIN
    FOREACH table_name IN ARRAY tables
    LOOP
        EXECUTE format('CREATE TABLE %I.%I (LIKE %I.%I INCLUDING ALL)', target_schema, table_name, source_schema, table_name);
        EXECUTE format('INSERT INTO %I.%I SELECT * FROM %I.%I', target_schema, table_name, source_schema, table_name);
    END LOOP;
END $$;
