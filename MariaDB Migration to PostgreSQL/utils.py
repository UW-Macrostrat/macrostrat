from sqlalchemy import text, create_engine, inspect
from Constants import *
import os
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd

import time

"""
Copies table structure and table data from one schema to another schema on the same host.
Command line in cmd.exe language
"""

def pg_dump(server, user, password, dbname, schema):
    pg_dump_command = f'pg_dump -h {server} -d {dbname} -U {user} --schema={schema} -W -F d -f ./postgres_dump'
    pg_dump_command_two = f'{password}'
    print(pg_dump_command)
    print(pg_dump_command_two)
    #os.system(pg_dump_command)
    #os.system(pg_dump_command_two)
    print('Starting database export........')
    return

def pg_restore(server, user, password, dbname, schema):
    pg_restore = f'pg_restore  -h {server} -d {dbname} -U {user} --schema={schema} -W -F d ./postgres_dump'
    pg_restore_two = f'{password}'
    print(pg_restore)
    print(pg_restore_two)

    return


def maria_dump(server, user, password, dbname):
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{user}:{password}@{server}/{dbname}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {maria_db_name_two};"))
    engine.dispose()
    output_file = './maria_dump.sql'
    maria_dump_command = [
        'mysqldump',
        '-h', server,
        '-d', dbname,
        '-u', user,
        f'-p{password}',
        '--ssl-verify-server-cert=false',
        '--no-data=false',
        '--verbose',
        '--result-file=./maria_dump.sql',
    ]
    os.system(' '.join(maria_dump_command))
    return


def maria_restore(server, user, password, dbname):

    maria_restore_input = f'mariadb -h {server} -u {user} -p{password} --ssl-verify-server-cert=false ' \
                          f'{dbname} < ./maria_dump.sql'

    print('Restoring new Maria database....')
    os.system(maria_restore_input)
    return


def get_data_counts_maria():
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{maria_super_user}:" \
                              f"{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    maria_rows = {}
    maria_columns = {}

    with engine.connect() as conn:
        tables_query = text(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{maria_db_name_two}'" \
                     " AND table_type = 'BASE TABLE';")
        row_result = conn.execute(tables_query)
        maria_tables = [row[0] for row in row_result]
        for table in maria_tables:
            row_query = text(f"SELECT COUNT(*) FROM {table};")
            row_result = conn.execute(row_query)
            row_count = row_result.scalar()
            maria_rows[table.lower()] = row_count

            column_query = text(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = '{maria_db_name_two}' AND table_name = '{table}';")
            column_result = conn.execute(column_query)
            column_count = column_result.scalar()
            maria_columns[table.lower()] = column_count

    engine.dispose()
    return maria_rows, maria_columns


def get_data_counts_pg(database_name, username, password, schema):
    SQLALCHEMY_DATABASE_URI = f"postgresql://{username}:{password}@{pg_server}/{database_name}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    pg_rows = {}
    pg_columns = {}

    with engine.connect() as conn:
        table_query = text(f"SELECT table_name FROM information_schema.tables WHERE table_catalog = '{database_name}'" \
                     " AND table_type = 'BASE TABLE'" \
                     f" AND table_schema = '{schema}'")
        table_result = conn.execute(table_query)
        pg_tables = [row[0] for row in table_result]
        for table in pg_tables:
            row_query = text(f"SELECT COUNT(*) FROM {database_name}.{schema}.{table};")
            row_result = conn.execute(row_query)
            row_count = row_result.scalar()
            pg_rows[table.lower()] = row_count

            column_query = text(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_catalog = '{database_name}' "
                                f"AND table_schema = '{schema}' AND table_name = '{table}';")
            column_result = conn.execute(column_query)
            column_count = column_result.scalar()
            pg_columns[table.lower()] = column_count
    engine.dispose()
    return pg_rows, pg_columns




"""
Compares the data counts between tables, rows, and columns that vary between any two db's
"""
def compare_data_counts(db1_rows, db2_rows, db1_columns, db2_columns, db1, db2):
    db1_rows_not_in_db2 = {table_name: (db1_rows[table_name], 0) for table_name in db1_rows if
                            table_name not in db2_rows}
    db2_rows_not_in_db1 = {table_name: (0, db2_rows[table_name]) for table_name in db2_rows if
                           table_name not in db1_rows}
    db1_cols_not_in_db2 = {table_name: (db1_columns[table_name], 0) for table_name in db1_columns if
                           table_name not in db2_columns}
    db2_cols_not_in_db1 = {table_name: (0, db2_columns[table_name]) for table_name in db2_columns if
                           table_name not in db1_columns}

    if len(db1_rows_not_in_db2) == 0 and len(db2_rows_not_in_db1) == 0:
        print(f"\nSuccess! All tables exist in both {db1} and {db2}. Checking row counts....\n")
    else:
        if len(db1_rows_not_in_db2) > 0:
            print(f'\nERROR: {db1} tables that are not in {db2}:\n', [key for key in db1_rows_not_in_db2])
        if len(db2_rows_not_in_db1) > 0:
            print(f'\nERROR: {db2} tables that are not in {db1}: \n', [key for key in db2_rows_not_in_db1])

    row_count_difference = {key: (db1_rows[key], db2_rows[key]) for key in db1_rows if
                            key in db2_rows and db1_rows[key] != db2_rows[key]}
    #row_count_difference.update(db1_rows_not_in_db2)
    #row_count_difference.update(db2_rows_not_in_db1)

    col_count_difference = {key: (db1_columns[key], db2_columns[key]) for key in db1_columns if
                            key in db2_columns and db1_columns[key] != db2_columns[key]}
    #col_count_difference.update(db1_cols_not_in_db2)
    #col_count_difference.update(db2_cols_not_in_db1)

    if len(row_count_difference) == 0:
        print(f"Success! All row counts in all tables are the same in both {db1} and {db2}!\n")
    else:
        print(f'\nERROR: Row count differences for {len(row_count_difference)} tables in both {db1} and {db2} databases:\n'
              f'Table Name: ({db1} Rows, {db2} Rows)\n'
              f'{row_count_difference}')
    if len(col_count_difference) == 0:
        print(f"Success! All column counts in all tables are the same in both {db1} and {db2}!\n")
    else:
        print(f'\nERROR: Column count differences for {len(col_count_difference)} tables in both {db1} and {db2} databases:\n'
              f'Table Name: ({db1} Columns, {db2} Columns)\n'
              f'{col_count_difference}')

    return row_count_difference, col_count_difference




def find_row_variances(database_name_one, schema_one, schema_two, username, password, tables):
    SQLALCHEMY_DATABASE_URI = f"postgresql://{username}:{password}@{pg_server}/{database_name_one}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    insp = inspect(engine)
    with engine.connect() as conn:
        for table in tables:
            # Get the actual first column name for each table
            columns = insp.get_columns(table, schema=schema_one)
            first_column_name = columns[0]['name']
            query = f"""
                   SELECT m.{first_column_name}
                   FROM macrostrat.macrostrat.{table} m
                   RIGHT JOIN macrostrat.macrostrat_temp.{table} t ON m.{first_column_name} = t.{first_column_name}
                   WHERE t.{first_column_name} IS NULL;
               """
            result_df = pd.read_sql_query(query, engine)
            print(f"Macrostrat rows not in Macrostrat_two rows for table {table}:")
            print(result_df)
    engine.dispose()
    return

#strat_tree column names renamed from this_name and that_name to parent and child in Macrostrat. Determine how to merge.
#possibly rename after the merge and update the API.

def find_col_variances(database_name_one, schema_one, schema_two, username, password, tables):
    SQLALCHEMY_DATABASE_URI = f"postgresql://{username}:{password}@{pg_server}/{database_name_one}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    insp = inspect(engine)
    table_one = []
    table_two = []
    col_not_in_macrostrat_two = []
    with engine.connect() as conn:
        for table in tables:
            dict = []
            dict_two = []
            table_one = []
            table_two = []
            columns_one = insp.get_columns(table, schema=schema_one)
            columns_two = insp.get_columns(table, schema=schema_two)
            for index in range(0, len(columns_one)-1):
                dict = columns_one[index]
                table_one.append(dict['name'])
            for index_two in range(0, len(columns_two)-1):
                dict_two = columns_two[index_two]
                table_two.append(dict_two['name'])
            for col in table_one:
                if col not in table_two:
                    col_not_in_macrostrat_two.append(col)
            if len(col_not_in_macrostrat_two) > 0:
                print(f"Columns that exist in Macrostrat and NOT in macrostrat_two for {table}:", col_not_in_macrostrat_two)
            else:
                print("Success! All columns in Macrostrat exist in Macrostrat_two")
    engine.dispose()
    return


def find_row_variances_primary_key(database_name_one, schema_one, schema_two, username, password, tables):
    SQLALCHEMY_DATABASE_URI = f"postgresql://{username}:{password}@{pg_server}/{database_name_one}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    insp = inspect(engine)
    with engine.connect() as conn:
        for table in tables:
            # Get the primary key constraint for each table
            pk_constraint = insp.get_pk_constraint(table, schema=schema_one)
            try:
                pk_column_name = pk_constraint['constrained_columns'][0]
            except Exception as e:
                pk_column_name = None
            if pk_column_name:
                query = f"""
                    SELECT m.{pk_column_name}
                    FROM macrostrat.macrostrat.{table} m
                    RIGHT JOIN macrostrat.macrostrat_temp.{table} t ON m.{pk_column_name} = t.{pk_column_name}
                    WHERE t.{pk_column_name} IS NULL;
                """
                result_df = pd.read_sql_query(query, engine)
                print(f"Macrostrat rows not in Macrostrat_two rows for table {table}:")
                print(result_df)
            else:
                print(f"Table macrostrat.{table} does not have a primary key.")
    engine.dispose()
    return


def pg_loader_pre_script():
    # Query alters the MariaDB tables by adding a new column for geom -> text data,
    # setting the datatype of the new column data to WKT format,
    # dropping the old geometry column,
    # adding default values for data formats that pgloader accepts
    query_pbdb_matches = """ALTER TABLE macrostrat_temp.pbdb_matches ADD COLUMN coordinate_point_text TEXT;
    UPDATE macrostrat_temp.pbdb_matches SET coordinate_point_text = ST_AsText(coordinate);
    ALTER TABLE macrostrat_temp.pbdb_matches DROP COLUMN coordinate;
    UPDATE macrostrat_temp.pbdb_matches SET release_date = '2000-01-01' WHERE release_date = '0000-00-00 00:00:00';"""

    query_places = """
        ALTER TABLE macrostrat_temp.places ADD COLUMN geom_text LONGTEXT;
        UPDATE macrostrat_temp.places
        SET geom_text = ST_AsText(geom);
        ALTER TABLE macrostrat_temp.places DROP COLUMN geom;
    """

    query_refs = """
        ALTER TABLE macrostrat_temp.refs ADD COLUMN rgeom_text LONGTEXT;
        UPDATE macrostrat_temp.refs
        SET rgeom_text = ST_AsText(rgeom);
        ALTER TABLE macrostrat_temp.refs DROP COLUMN rgeom;
    """

    query_unit_contacts = """
        UPDATE unit_contacts
        -- Enum data type can't be null so set to enum option 'below'.
        SET contact = 'below'
        WHERE contact = '';
        UPDATE unit_contacts
        -- enum data type can't be null so set to enum option 'above'.
        SET old_contact = 'above'
        WHERE old_contact = '';
    """

    query_cols = """
        ALTER TABLE macrostrat_temp.cols ADD COLUMN coordinate_text LONGTEXT;
        UPDATE macrostrat_temp.cols
        SET coordinate_text = ST_AsText(coordinate);
        ALTER TABLE macrostrat_temp.cols DROP COLUMN coordinate;
        UPDATE macrostrat_temp.cols
        SET created = '2000-01-01'
        WHERE created = '0000-00-00 00:00:00';
    """

    query_col_areas = """
        ALTER TABLE macrostrat_temp.col_areas ADD COLUMN col_area_text LONGTEXT;
        UPDATE macrostrat_temp.col_areas
        SET col_areas.col_area_text = ST_AsText(col_area);
        ALTER TABLE macrostrat_temp.col_areas DROP COLUMN col_area;

    """

    query_col_areas_6April2016 = """
        ALTER TABLE macrostrat_temp.col_areas_6April2016 ADD COLUMN col_area_text LONGTEXT;
        UPDATE macrostrat_temp.col_areas_6April2016
        SET col_areas_6April2016.col_area_text = ST_AsText(col_area);
        ALTER TABLE macrostrat_temp.col_areas_6April2016 DROP COLUMN col_area;
    """

    query_liths = """
    UPDATE macrostrat_temp.liths
    SET macrostrat_temp.lith_group = null
    where macrostrat_temp.lith_group = '';"""

    pre_script_queries = [query_pbdb_matches, query_places, query_refs, query_unit_contacts, query_cols, query_col_areas,
                          query_col_areas_6April2016, query_liths]

    URL = f"mysql+pymysql://{maria_super_user}:{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    engine = create_engine(URL)
    with engine.connect() as conn:
        for query in pre_script_queries:
            statements = query.split(';')
            for statement in statements:
                if statement.strip():
                    try:
                        conn.execute(text(statement))
                        print(f"Successfully executed: {statement}")
                    except Exception as e:
                        print(f"Error with statement: {statement}\n{e}")
    engine.dispose()
    return
'''
    #create db, create temp user before pgloader
    URL = f"postgresql://{pg_user}:{pg_pass_new}@{pg_server}/{pg_db_name}"
    pg_engine = create_engine(URL)
    with pg_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {pg_db_name_two}"))
        conn.execute(text(f"DROP USER IF EXISTS {pg_user_maria_temp};"))
        conn.execute(text(f"CREATE USER maria_migrate WITH PASSWORD '{pg_pass_maria_temp}'"))
        conn.execute(text(f"GRANT CONNECT ON DATABASE {pg_db_name_two} TO {pg_user_maria_temp};"))
    pg_engine.dispose()'''



def pg_loader_post_script():
    # Query alters the MariaDB pbdb_matches table by adding a new column for the text data,
    # setting the datatype of the new column data to WKT format,
    # dropping the old geometry column,
    # adding default values for data formats that pgloader accepts
    #vaccuum...refresh postgresql database after pgloader
    #CREATE EXTENSION IF NOT EXISTS postgis;
    SQLALCHEMY_DATABASE_URI = f"postgresql://{pg_user_migrate}:{pg_pass_migrate}@{pg_server}/{pg_db_name_two}?sslmode=prefer"
    engine = create_engine(SQLALCHEMY_DATABASE_URI) #connect_args={'options': '-csearch_path=public,macrostrat_temp'


    query_pbdb_matches = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.pbdb_matches ADD COLUMN coordinate geometry(Point, 4326);
        UPDATE macrostrat_two.macrostrat_temp.pbdb_matches SET coordinate = ST_GeomFromText(coordinate_point_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.pbdb_matches DROP COLUMN coordinate_point_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.pbdb_matches LIMIT 5;""")

    query_places = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.places ADD COLUMN geom geometry;
        UPDATE macrostrat_two.macrostrat_temp.places SET geom = ST_GeomFromText(geom_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.places DROP COLUMN geom_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.places LIMIT 5;""")

    query_refs = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.refs ADD COLUMN rgeom geometry;
        UPDATE macrostrat_two.macrostrat_temp.refs SET rgeom = ST_GeomFromText(rgeom_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.refs DROP COLUMN rgeom_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.refs LIMIT 5;""")


    query_cols = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.cols ADD COLUMN coordinate geometry;
        UPDATE macrostrat_two.macrostrat_temp.cols SET coordinate = ST_GeomFromText(coordinate_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.cols DROP COLUMN coordinate_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.cols LIMIT 5;""")

    query_col_areas = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.col_areas ADD COLUMN col_area geometry;
        UPDATE macrostrat_two.macrostrat_temp.col_areas SET col_area = ST_GeomFromText(col_area_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.col_areas DROP COLUMN col_area_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.col_areas LIMIT 5;""")

    query_col_areas_6April2016 = text("""
        ALTER TABLE macrostrat_two.macrostrat_temp.col_areas_6April2016 ADD COLUMN col_area geometry;
        UPDATE macrostrat_two.macrostrat_temp.col_areas_6April2016 SET col_area = ST_GeomFromText(col_area_text, 4326);
        ALTER TABLE macrostrat_two.macrostrat_temp.col_areas_6April2016 DROP COLUMN col_area_text;
        SELECT * FROM macrostrat_two.macrostrat_temp.col_areas_6April2016 LIMIT 5;""")

    post_script_queries = [query_pbdb_matches, query_refs, query_cols, query_places, query_col_areas, query_col_areas_6April2016]
    print('Starting PostScript execution....')
    with engine.connect() as conn:
        for query in post_script_queries:
            try:
                result = conn.execute(query.execution_options(autocommit=True))
                for row in result:
                    print(row)
            except SQLAlchemyError as e:
                print(f"Error: {e}")
                #rollback the transaction if an error occurs
                conn.execute(text("ROLLBACK;"))

    engine.dispose()
    return

def pg_loader():
    """
    Command terminal to run pgloader. Ensure Docker app is running.
    """
    dockerfile_content = "FROM dimitri/pgloader:latest\n" \
                         "RUN apt-get update && apt-get install -y postgresql-client\n" \
                         "RUN apt-get install -y ca-certificates"
    with open("Dockerfile", "w") as dockerfile:
        dockerfile.write(dockerfile_content)
    os.system("docker build -t pgloader-test .")


    input_command = f"--with \"prefetch rows = 1000\" --verbose " \
                    f"mysql://root:{maria_super_pass}@{maria_server}/{maria_db_name_two} " \
                    f"postgresql://{pg_user_migrate}:{pg_pass_migrate}@{pg_server}/{pg_db_name_two}?sslmode=prefer"

    print(input_command)
    os.system(f"docker run -i --rm pgloader-test pgloader {input_command}")
    return


def reset():
    SQLALCHEMY_DATABASE_URI = f"{pg_user_maria_temp}:{pg_pass_maria_temp}@{pg_server}/{pg_db_name_two}"
    pg_engine = create_engine(SQLALCHEMY_DATABASE_URI)
    pg_drop_query = text(f"DROP SCHEMA macrostrat_temp CASCADE") # {new_migrate_schema_name}

    with pg_engine.connect() as conn:
        conn.execute(pg_drop_query)
    pg_engine.dispose()

    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{maria_super_user}:" \
                              f"{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    maria_engine = create_engine(SQLALCHEMY_DATABASE_URI)
    maria_drop_query = text(f"DROP DATABASE {maria_db_name_two}")

    with maria_engine.connect() as conn:
        conn.execute(maria_drop_query)
    maria_engine.dispose()




if __name__ == "__main__":
    #maria_dump(maria_server, maria_super_user, maria_super_pass, maria_db_name)
    #maria_restore(maria_server, maria_super_user, maria_super_pass, maria_db_name_two)
    #pg_loader_pre_script()
    #pg_loader()
    #pg_loader_post_script()
    #maria_rows, maria_columns = get_data_counts_maria()
    #pg_rows, pg_columns = get_data_counts_pg(pg_db_name, pg_user, pg_pass_new, 'macrostrat')
    #pg_macrostrat_two_rows, pg_macrostrat_two_columns = get_data_counts_pg(pg_db_name_two, pg_user_migrate, pg_pass_migrate, 'macrostrat_temp')

    #print('\nMARIADB (db1) comparison to PG MACROSTRAT_TWO (db2). These should be clones. ')
    #db1 = 'MariaDB'
    #db2 = 'PG Macrostrat_Two'
    #row_variance, column_variance = compare_data_counts(maria_rows, pg_macrostrat_two_rows, maria_columns,
     #                                                   pg_macrostrat_two_columns, db1, db2)
    #print('\nPG MACROSTRAT_TWO (db1 maria db clone) comparison to PG MACROSTRAT (db2). This will show what data '
     #     'needs to be moved over from Maria to PG prod.')
    #db1 = 'PG Macrostrat_Two'
    #db2 = 'PG Macrostrat'
    #row_variance_two, column_variance_two = compare_data_counts(pg_macrostrat_two_rows, pg_rows, pg_macrostrat_two_columns,
     #                                                   pg_columns, db1, db2)
    #reset()
    pg_restore(pg_server, pg_user, pg_pass_new, pg_db_name, maria_db_name_two)

    table_rows = [
        "sections",
        "strat_names",
        "strat_names_places",
        "strat_tree",
        "units",
        "timescales",
        "timescales_intervals",
        "units_sections",
        "unit_boundaries",
        "unit_econs",
        "unit_measures",
        "unit_strat_names",
        "unit_environs",
        "unit_liths",
        "autocomplete",
        "cols",
        "col_areas",
        "col_groups",
        "col_refs",
        "intervals",
        "liths",
        "lookup_strat_names",
        "lookup_units",
        "lookup_unit_attrs_api",
        "lookup_unit_intervals",
        "refs"
    ]

    table_cols = ['sections',
                  'strat_names',
                  'strat_tree',
                  'units',
                  'unit_strat_names',
                  'unit_environs',
                  'cols',
                  'environs',
                  'lith_atts',
                  'lookup_strat_names',
                  'lookup_unit_intervals',
                  'measuremeta',
                  'measures']


    #results = find_row_variances(pg_db_name, pg_db_name, maria_db_name_two, pg_user, pg_pass_new, table_rows)

    results_two = find_col_variances(pg_db_name, pg_db_name, maria_db_name_two, pg_user, pg_pass_new, table_cols)
