from sqlalchemy import text, create_engine
from Constants import *
import os
from macrostrat.database.utils import run_sql
from pathlib import Path

import time
from .db_changes import get_data_counts_maria, get_data_counts_pg, compare_data_counts

"""
Copies table structure and table data from one schema to another schema on the same host.
Command line in cmd.exe language
"""

__here__ = Path(__file__).parent


def pg_dump(server, user, password, dbname):
    # TODO: integrate with existing PostgreSQL database utilities
    os.system(
        f"pg_dump  -h {pg_server} -d {pg_db_name} -U {pg_user} -W -F d -f ./postgres_dump"
    )
    os.system(f"{pg_pass}")
    print("Starting database export........")
    return


def pg_restore(server, user, password, dbname):
    # TODO: integrate with existing PostgreSQL database utilities
    os.system(
        f"pg_dump  -h {pg_server} -d {pg_db_name_two} -U {pg_user} -W -F d ./postgres_dump"
    )
    os.system(f"{pg_pass}")
    return


def maria_dump(server, user, password, dbname):
    # TODO: integrate with streaming approach
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{user}:{password}@{server}/{dbname}"
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {maria_db_name_two};"))
    engine.dispose()
    output_file = "./maria_dump.sql"
    maria_dump_command = [
        "mysqldump",
        "-h",
        server,
        "-d",
        dbname,
        "-u",
        user,
        f"-p{password}",
        "--ssl-verify-server-cert=false",
        "--no-data=false",
        "--verbose",
        "--result-file=./maria_dump.sql",
    ]
    os.system(" ".join(maria_dump_command))
    return


def maria_restore(server, user, password, dbname):

    maria_restore_input = (
        f"mariadb -h {server} -u {user} -p{password} --ssl-verify-server-cert=false "
        f"{dbname} < ./maria_dump.sql"
    )

    print("Restoring new Maria database....")
    os.system(maria_restore_input)
    return


"""
Script to output dataframes for comparing data between two databases and tables.
"""


def pg_loader_pre_script():
    pre_script = __here__ / "pgloader-pre-script.sql"

    URL = f"mysql+pymysql://{maria_super_user}:{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    engine = create_engine(URL)
    run_sql(engine, pre_script)
    engine.dispose()


"""
    #create db, create temp user before pgloader
    URL = f"postgresql://{pg_user}:{pg_pass_new}@{pg_server}/{pg_db_name}"
    pg_engine = create_engine(URL)
    with pg_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {pg_db_name_two}"))
        conn.execute(text(f"DROP USER IF EXISTS {pg_user_maria_temp};"))
        conn.execute(text(f"CREATE USER maria_migrate WITH PASSWORD '{pg_pass_maria_temp}'"))
        conn.execute(text(f"GRANT CONNECT ON DATABASE {pg_db_name_two} TO {pg_user_maria_temp};"))
    pg_engine.dispose()"""


def pg_loader_post_script():
    # Query alters the MariaDB pbdb_matches table by adding a new column for the text data,
    # setting the datatype of the new column data to WKT format,
    # dropping the old geometry column,
    # adding default values for data formats that pgloader accepts
    # vaccuum...refresh postgresql database after pgloader
    # CREATE EXTENSION IF NOT EXISTS postgis;
    SQLALCHEMY_DATABASE_URI = f"postgresql://{pg_user_migrate}:{pg_pass_migrate}@{pg_server}/{pg_db_name_two}?sslmode=prefer"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URI
    )  # connect_args={'options': '-csearch_path=public,macrostrat_temp'

    print("Starting PostScript execution....")
    post_script = __here__ / "pgloader-post-script.sql"
    run_sql(engine, post_script)


def pg_loader():
    """
    Command terminal to run pgloader. Ensure Docker app is running.
    """
    dockerfile_content = (
        "FROM dimitri/pgloader:latest\n"
        "RUN apt-get update && apt-get install -y postgresql-client\n"
        "RUN apt-get install -y ca-certificates"
    )
    with open("Dockerfile", "w") as dockerfile:
        dockerfile.write(dockerfile_content)
    os.system("docker build -t pgloader-test .")

    input_command = (
        f'--with "prefetch rows = 1000" --verbose '
        f"mysql://root:{maria_super_pass}@{maria_server}/{maria_db_name_two} "
        f"postgresql://{pg_user_migrate}:{pg_pass_migrate}@{pg_server}/{pg_db_name_two}?sslmode=prefer"
    )

    print(input_command)
    os.system(f"docker run -i --rm pgloader-test pgloader {input_command}")
    return


def reset():
    SQLALCHEMY_DATABASE_URI = (
        f"{pg_user_maria_temp}:{pg_pass_maria_temp}@{pg_server}/{pg_db_name_two}"
    )
    pg_engine = create_engine(SQLALCHEMY_DATABASE_URI)
    pg_drop_query = text(
        f"DROP SCHEMA macrostrat_temp CASCADE"
    )  # {new_migrate_schema_name}

    with pg_engine.connect() as conn:
        conn.execute(pg_drop_query)
    pg_engine.dispose()

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{maria_super_user}:"
        f"{maria_super_pass}@{maria_server}/{maria_db_name_two}"
    )
    maria_engine = create_engine(SQLALCHEMY_DATABASE_URI)
    maria_drop_query = text(f"DROP DATABASE {maria_db_name_two}")

    with maria_engine.connect() as conn:
        conn.execute(maria_drop_query)
    maria_engine.dispose()


if __name__ == "__main__":
    # maria_dump(maria_server, maria_super_user, maria_super_pass, maria_db_name)
    # maria_restore(maria_server, maria_super_user, maria_super_pass, maria_db_name_two)
    # pg_loader_pre_script()
    # pg_loader()
    # pg_loader_post_script()
    maria_rows, maria_columns = get_data_counts_maria()
    pg_rows, pg_columns = get_data_counts_pg(
        pg_db_name, pg_user, pg_pass_new, "macrostrat"
    )
    pg_macrostrat_two_rows, pg_macrostrat_two_columns = get_data_counts_pg(
        pg_db_name_two, pg_user_migrate, pg_pass_migrate, "macrostrat_temp"
    )

    print(
        "\nMARIADB (db1) comparison to PG MACROSTRAT_TWO (db2). These should be clones. "
    )
    db1 = "MariaDB"
    db2 = "PG Macrostrat_Two"
    row_variance, column_variance = compare_data_counts(
        maria_rows,
        pg_macrostrat_two_rows,
        maria_columns,
        pg_macrostrat_two_columns,
        db1,
        db2,
    )
    print(
        "\nPG MACROSTRAT_TWO (db1 maria db clone) comparison to PG MACROSTRAT (db2). This will show what data "
        "needs to be moved over from Maria to PG prod."
    )
    db1 = "PG Macrostrat_Two"
    db2 = "PG Macrostrat"
    row_variance_two, column_variance_two = compare_data_counts(
        pg_macrostrat_two_rows, pg_rows, pg_macrostrat_two_columns, pg_columns, db1, db2
    )
    # reset()
    # df, df_two = find_row_variances(pg_db_name, pg_db_name, pg_db_name_two, maria_db_name_two,
    # pg_user, pg_pass_new, 'cols')
