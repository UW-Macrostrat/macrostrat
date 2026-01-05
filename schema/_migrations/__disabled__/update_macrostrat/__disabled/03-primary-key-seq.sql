/* Add sequences and set next vals to be whatever the current max is */

CREATE OR REPLACE FUNCTION macrostrat.make_into_serial(schema_name TEXT, table_name TEXT, column_name TEXT) RETURNS INTEGER AS $$
DECLARE
    start_with INTEGER;
    sequence_name TEXT;
    schema_table_name TEXT;
    owner regrole;
BEGIN

    EXECUTE 'SELECT relowner::regrole FROM pg_class WHERE relname = $1 AND  relnamespace::text = $2' INTO owner USING table_name, schema_name;

    sequence_name := table_name || '_' || column_name || '_seq';
    schema_table_name := quote_ident(schema_name) || '.' || quote_ident(table_name);
    EXECUTE format('SELECT coalesce(max(%I), 0) + 1 FROM %I.%I', column_name, schema_name, table_name)
            INTO start_with;

    EXECUTE format('CREATE SEQUENCE IF NOT EXISTS %I.%I '
        'START WITH $1 '
        'OWNED BY %I',
        schema_name, sequence_name, schema_name, owner) USING start_with;

    EXECUTE format('ALTER SEQUENCE %I.%I OWNED BY %I.%I.%I', schema_name, sequence_name, schema_name, table_name, column_name);

    EXECUTE format('SELECT setval($1, $2) FROM %I.%I', schema_name, table_name) USING sequence_name, start_with;
    EXECUTE 'ALTER TABLE ' || schema_table_name || ' ALTER COLUMN ' || column_name ||
            ' SET DEFAULT nextVal(' || quote_literal(sequence_name) || ')';
    RETURN start_with;
END;
$$ LANGUAGE plpgsql VOLATILE;


/* loop through all primary keys in macrostrat schema and reset add auto-incrementing sequence */
CREATE OR REPLACE PROCEDURE macrostrat.pg_reset_pkey_seq()
AS
$$
DECLARE
	sql_reset TEXT;
	table_pkeys RECORD;
	next_val INT;
BEGIN

sql_reset :=
$sql$
SELECT macrostrat.make_into_serial('%1$s', '%2$s', '%3$s');
$sql$;

FOR table_pkeys IN
	SELECT kcu.table_schema, kcu.table_name, kcu.column_name
	FROM information_schema.key_column_usage kcu
	JOIN information_schema.table_constraints tc
	ON tc.constraint_name = kcu.constraint_name
	WHERE tc.constraint_type='PRIMARY KEY'
	AND kcu.table_schema='macrostrat'
LOOP
	EXECUTE format(sql_reset, table_pkeys.table_schema,table_pkeys.table_name,table_pkeys.column_name) INTO next_val;
	RAISE info 'Resetting sequence for: %.% (%) to %'
		, table_pkeys.table_schema
		, table_pkeys.table_name
		, table_pkeys.column_name
		, next_val
		;
END LOOP;
END
$$
LANGUAGE plpgsql;

call macrostrat.pg_reset_pkey_seq();
