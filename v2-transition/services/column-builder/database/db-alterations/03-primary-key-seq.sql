/* Add sequences and set next vals to be whatever the current max is */

CREATE OR REPLACE FUNCTION macrostrat.make_into_serial(table_name TEXT, column_name TEXT) RETURNS INTEGER AS $$
DECLARE
    start_with INTEGER;
    sequence_name TEXT;
BEGIN
    sequence_name := table_name || '_' || column_name || '_seq';
    EXECUTE 'SELECT coalesce(max(' || column_name || '), 0) + 1 FROM ' || table_name
            INTO start_with;
    EXECUTE 'CREATE SEQUENCE IF NOT EXISTS ' || sequence_name ||
            ' START WITH ' || start_with ||
            ' OWNED BY ' || table_name || '.' || column_name;
    EXECUTE 'SELECT setval(' || quote_literal(sequence_name)|| ',' || start_with || ') FROM ' || table_name;
    EXECUTE 'ALTER TABLE ' || table_name || ' ALTER COLUMN ' || column_name ||
            ' SET DEFAULT nextVal(''' || sequence_name || ''')';
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
SELECT macrostrat.make_into_serial('%1$s.%2$s', '%3$s');
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
	RAISE info 'Resetting Sequence for: %.% (%) to %'
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