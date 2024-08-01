"""
Script to output dataframes for comparing data between two databases and tables.
"""

import pandas as pd
from macrostrat.database import run_query
from psycopg2.sql import Identifier
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from macrostrat.core import app

console = app.console


def get_data_counts_maria(engine: Engine):
    db_name = engine.url.database
    maria_rows = {}
    maria_columns = {}

    with engine.connect() as conn:
        row_result = run_query(
            conn,
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :table_schema AND table_type = 'BASE TABLE'",
            {"table_schema": db_name},
        )

        maria_tables = [row[0] for row in row_result]
        for table in maria_tables:
            row_result = run_query(conn, f"SELECT COUNT(*) FROM {table}")
            row_count = row_result.scalar()
            maria_rows[table.lower()] = row_count
            column_result = run_query(
                conn,
                "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = :table_schema AND table_name = :table_name",
                dict(table_schema=db_name, table_name=table),
            )

            column_count = column_result.scalar()
            maria_columns[table.lower()] = column_count

    engine.dispose()
    return maria_rows, maria_columns


def get_data_counts_pg(engine: Engine, schema):
    database_name = engine.url.database

    pg_rows = {}
    pg_columns = {}

    with engine.connect() as conn:
        table_result = run_query(
            conn,
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_catalog = :table_catalog
            AND table_type = 'BASE TABLE' AND table_schema = :table_schema
            """,
            dict(table_schema=schema, table_catalog=database_name),
        )
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
                conn,
                """
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_catalog = :table_catalog
                  AND table_schema = :schema
                  AND table_name = :table
                """,
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
        success(f"All tables exist in both {db1} and {db2}.")
    else:
        if len(db1_rows_not_in_db2) > 0:
            error(f"{len(db1_rows_not_in_db2)} {db1} tables not found in {db2}:")
            console.print(
                [key for key in db1_rows_not_in_db2],
            )
        if len(db2_rows_not_in_db1) > 0:
            error(f"{len(db2_rows_not_in_db1)} {db2} tables not found in {db1}:")
            console.print(
                [key for key in db2_rows_not_in_db1],
            )

    console.print("\n[bold]Checking row counts...")

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
        success(f"All row counts in all tables are the same in {db1} and {db2}!")
    else:
        error(
            f"Row count differences for {len(row_count_difference)} tables in {db1} and {db2} databases"
        )
        print_counts(row_count_difference)

    if len(col_count_difference) == 0:
        success(f"All column counts in all tables are the same in {db1} and {db2}!\n")
    else:
        error(
            f"Column count differences for {len(col_count_difference)} tables in {db1} and {db2} databases"
        )
        print_counts(col_count_difference)

    return row_count_difference, col_count_difference


def print_counts(counts):
    for key, (v1, v2) in counts.items():
        diff = v1 - v2
        col = "red" if diff < 0 else "green"
        diff = f"[{col}]{diff:+8d}[/]"

        console.print(f"{key:30s} {v1:9d} {v2:9d} [dim]{diff}[/dim]")


def error(message):
    console.print(f"\n[red bold]ERROR:[red] {message}")


def success(message):
    console.print(f"\n[green bold]SUCCESS:[green] {message}")


def find_row_variances(
        database_name_one,
        schema_one,
        schema_two,
        username,
        password,
        tables,
        pg_engine
):
    insp = inspect(pg_engine)
    count = 0
    with pg_engine.connect() as conn:
        for table in tables:
            # Get the actual first column name for each table
            columns = insp.get_columns(table, schema=schema_one)
            first_column_name = columns[0]['name']
            query = f"""
                   SELECT COUNT(m.{first_column_name})
                   FROM macrostrat.macrostrat.{table} m
                   RIGHT JOIN macrostrat.macrostrat_temp.{table} t ON m.{first_column_name} = t.{first_column_name}
                   WHERE t.{first_column_name} IS NULL;
               """
            result = conn.execute(text(query))
            for row in result:
                print(row[0], table)
        pg_engine.dispose()
    return

def find_col_variances(
    database_name_one,
    schema_one,
    schema_two,
    username,
    password,
    tables,
    pg_engine
):

    insp = inspect(pg_engine)
    for table in tables:
        columns_one = insp.get_columns(table, schema=schema_one)
        columns_two = insp.get_columns(table, schema=schema_two)
        col_names_one = {col['name'] for col in columns_one}
        col_names_two = {col['name'] for col in columns_two}
        col_not_in_schema_two = col_names_one - col_names_two
        if col_not_in_schema_two:
            print(f"Columns that exist in {schema_one} but NOT in {schema_two} for {table}: {col_not_in_schema_two}")
        else:
            print(f"All columns in {schema_one} exist in {schema_two} for {table}")
    pg_engine.dispose()
    return
