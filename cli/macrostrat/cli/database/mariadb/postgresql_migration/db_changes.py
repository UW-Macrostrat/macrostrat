import pandas as pd
from macrostrat.database import run_query
from psycopg2.sql import Identifier
from sqlalchemy import create_engine, text


def get_data_counts_maria():
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{maria_super_user}:"
        f"{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    maria_rows = {}
    maria_columns = {}

    with engine.connect() as conn:
        row_result = run_query(
            conn,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :table_schema AND table_type = 'BASE TABLE'",
            {"table_schema": maria_db_name_two},
        )

        maria_tables = [row[0] for row in row_result]
        for table in maria_tables:
            row_result = run_query(
                conn, "SELECT COUNT(*) FROM {table}", dict(table=Identifier(table))
            )
            row_count = row_result.scalar()
            maria_rows[table.lower()] = row_count
            column_result = run_query(
                conn,
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = :table_schema AND table_name = :table_name",
                dict(table_schema=maria_db_name_two, table_name=table),
            )

            column_count = column_result.scalar()
            maria_columns[table.lower()] = column_count

    engine.dispose()
    return maria_rows, maria_columns


def get_data_counts_pg(database_name, username, password, schema):
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{username}:{password}@{pg_server}/{database_name}"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    pg_rows = {}
    pg_columns = {}

    with engine.connect() as conn:
        table_query = run_query(
            conn,
            """SELECT table_name FROM information_schema.tables WHERE table_catalog = :table_catalog
             AND table_type = 'BASE TABLE' AND table_schema = :table_schema""",
            dict(table_schema=schema, table_catalog=database_name),
        )

        table_result = conn.execute(table_query)
        pg_tables = [row[0] for row in table_result]
        for table in pg_tables:
            row_result = run_query(
                conn,
                "SELECT COUNT(*) FROM {table}",
                dict(table=Identifier(schema, table)),
            )
            row_count = row_result.scalar()
            pg_rows[table.lower()] = row_count

            column_result = run_query(
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_catalog = :table_catalog AND table_schema = :schema AND table_name = :table",
                dict(table_catalog=database_name, schema=schema, table=table),
            )
            column_count = column_result.scalar()
            pg_columns[table.lower()] = column_count
    engine.dispose()
    return pg_rows, pg_columns


def compare_data_counts(db1_rows, db2_rows, db1_columns, db2_columns, db1, db2):
    """
    Compares the data counts between tables, rows, and columns that vary between any two db's
    """

    db1_rows_not_in_db2 = {
        table_name: (db1_rows[table_name], 0)
        for table_name in db1_rows
        if table_name not in db2_rows
    }
    db2_rows_not_in_db1 = {
        table_name: (0, db2_rows[table_name])
        for table_name in db2_rows
        if table_name not in db1_rows
    }
    db1_cols_not_in_db2 = {
        table_name: (db1_columns[table_name], 0)
        for table_name in db1_columns
        if table_name not in db2_columns
    }
    db2_cols_not_in_db1 = {
        table_name: (0, db2_columns[table_name])
        for table_name in db2_columns
        if table_name not in db1_columns
    }

    if len(db1_rows_not_in_db2) == 0 and len(db2_rows_not_in_db1) == 0:
        print(
            f"\nSuccess! All tables exist in both {db1} and {db2}. Checking row counts....\n"
        )
    else:
        if len(db1_rows_not_in_db2) > 0:
            print(
                f"\nERROR: {db1} tables that are not in {db2}:\n",
                [key for key in db1_rows_not_in_db2],
            )
        if len(db2_rows_not_in_db1) > 0:
            print(
                f"\nERROR: {db2} tables that are not in {db1}: \n",
                [key for key in db2_rows_not_in_db1],
            )

    row_count_difference = {
        key: (db1_rows[key], db2_rows[key])
        for key in db1_rows
        if key in db2_rows and db1_rows[key] != db2_rows[key]
    }
    # row_count_difference.update(db1_rows_not_in_db2)
    # row_count_difference.update(db2_rows_not_in_db1)

    col_count_difference = {
        key: (db1_columns[key], db2_columns[key])
        for key in db1_columns
        if key in db2_columns and db1_columns[key] != db2_columns[key]
    }
    # col_count_difference.update(db1_cols_not_in_db2)
    # col_count_difference.update(db2_cols_not_in_db1)

    if len(row_count_difference) == 0:
        print(
            f"Success! All row counts in all tables are the same in both {db1} and {db2}!\n"
        )
    else:
        print(
            f"\nERROR: Row count differences for {len(row_count_difference)} tables in both {db1} and {db2} databases:\n"
            f"Table Name: ({db1} Rows, {db2} Rows)\n"
            f"{row_count_difference}"
        )
    if len(col_count_difference) == 0:
        print(
            f"Success! All column counts in all tables are the same in both {db1} and {db2}!\n"
        )
    else:
        print(
            f"\nERROR: Column count differences for {len(col_count_difference)} tables in both {db1} and {db2} databases:\n"
            f"Table Name: ({db1} Columns, {db2} Columns)\n"
            f"{col_count_difference}"
        )

    return row_count_difference, col_count_difference


def find_row_variances(
    database_name_one,
    schema_one,
    database_name_two,
    schema_two,
    username,
    password,
    table,
):
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{username}:{password}@{pg_server}/{database_name_one}"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        query = text(f"SELECT * FROM {schema_one}.{table}")
    result = conn.execute(query)
    df = pd.DataFrame(result)
    engine.dispose()
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{username}:{password}@{pg_server}/{database_name_two}"
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        query = text(f"SELECT * FROM {schema_two}.{table}")
    result = conn.execute(query)
    df_two = pd.DataFrame(result)
    engine.dispose()
    return df, df_two
