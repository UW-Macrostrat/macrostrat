from io import StringIO

import docker
from sqlalchemy import text, create_engine
import os
from macrostrat.database.utils import run_sql
from macrostrat.app_frame.exc import ApplicationError
from pathlib import Path
from sqlalchemy.engine import Engine
from macrostrat.database import database_exists, create_database, drop_database
from ..restore import copy_mariadb_database
from ...._dev.utils import raw_database_url
from ...utils import engine_for_db_name, docker_internal_url
from ..._legacy import get_db
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run
from macrostrat.core import app
from textwrap import dedent
import docker
from io import BytesIO

import time
from .db_changes import get_data_counts_maria, get_data_counts_pg, compare_data_counts

__here__ = Path(__file__).parent

log = get_logger(__name__)


def migrate_mariadb_to_postgresql(
    maria_engine: Engine, pg_engine: Engine, overwrite: bool = False
):
    """Migrate the entire Macrostrat database from MariaDB to PostgreSQL."""
    temp_db_name = maria_engine.url.database + "_temp"

    maria_temp_engine = create_engine(maria_engine.url.set(database=temp_db_name))

    if database_exists(maria_temp_engine.url) and not overwrite:
        header(
            "Database [bold cyan]macrostrat_temp[/] already exists. Use --overwrite to overwrite."
        )
    else:
        copy_mariadb_database(maria_engine, maria_temp_engine, overwrite=overwrite)

    pg_temp_engine = create_engine(pg_engine.url.set(database=temp_db_name))

    pgloader_pre_script(maria_temp_engine)

    pgloader(maria_temp_engine, pg_temp_engine, overwrite=overwrite)

    pgloader_post_script(pg_temp_engine)

    compare_row_counts(maria_engine, pg_temp_engine, pg_engine)


def pgloader_pre_script(engine: Engine):
    assert engine.url.drivername.startswith("mysql")
    pre_script = __here__ / "pgloader-pre-script.sql"
    run_sql(engine, pre_script)


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


def pgloader_post_script(engine: Engine):
    app.console.print("\n[bold]Running post-migration script[/]")
    assert engine.url.drivername.startswith("postgres")
    post_script = __here__ / "pgloader-post-script.sql"
    run_sql(engine, post_script)


def pgloader(source: Engine, dest: Engine, overwrite=False):
    """
    Command terminal to run pgloader. Ensure Docker app is running.
    """
    db_exists = database_exists(dest.url)

    if db_exists:
        if overwrite:
            header("Dropping PostgreSQL database")
            drop_database(dest.url)
            db_exists = False
        else:
            header(
                f"PostgreSQL database [bold cyan]{dest.url.database}[/] already exists. Skipping pgloader."
            )
            return

    if not db_exists:
        header("Creating PostgreSQL database")
        create_database(dest.url)

    header("Building pgloader-runner Docker image")

    dockerfile = dedent(
        """FROM dimitri/pgloader:latest
        RUN apt-get update && apt-get install -y postgresql-client ca-certificates && rm -rf /var/lib/apt/lists/*
        ENTRYPOINT ["pgloader"]
        """
    )

    run(
        "docker",
        "build",
        "-t",
        "pgloader-runner:latest",
        "-",
        input=dockerfile.encode("utf-8"),
    )

    header("Running pgloader")

    # PyMySQL is not installed in the pgloader image, so we need to use the mysql client
    # to connect to the MariaDB database.
    source_url = source.url.set(drivername="mysql")

    run(
        "docker",
        "run",
        "-i",
        "--rm",
        "pgloader-runner",
        "--with",
        "prefetch rows = 1000",
        "--verbose",
        raw_database_url(docker_internal_url(source_url)),
        raw_database_url(docker_internal_url(dest.url)),
    )


def compare_row_counts(maria: Engine, pg_temp: Engine, pg_final: Engine):

    console = app.console

    maria_rows, maria_columns = get_data_counts_maria(maria)
    pg_macrostrat_temp_rows, pg_macrostrat_temp_columns = get_data_counts_pg(
        pg_temp, "macrostrat_temp"
    )

    db1 = db_identifier(maria)
    db2 = db_identifier(pg_temp)
    db3 = db_identifier(pg_final)

    header(f"\n\nComparing [cyan]{db1}[/] to [cyan]{db2}[/].")

    row_variance, column_variance = compare_data_counts(
        maria_rows,
        pg_macrostrat_temp_rows,
        maria_columns,
        pg_macrostrat_temp_columns,
        db1,
        db2,
    )

    pg_rows, pg_columns = get_data_counts_pg(pg_final, "macrostrat")

    header(f"\n\nComparing [cyan]{db2}[/] to [cyan]{db3}[/].")

    row_variance_two, column_variance_two = compare_data_counts(
        pg_macrostrat_temp_rows,
        pg_rows,
        pg_macrostrat_temp_columns,
        pg_columns,
        db2,
        db3,
    )
    # reset()
    # df, df_two = find_row_variances(pg_db_name, pg_db_name, pg_db_name_two, maria_db_name_two,
    # pg_user, pg_pass_new, 'cols')


def db_identifier(engine: Engine):
    driver = engine.url.drivername
    if driver.startswith("postgresql"):
        driver = "PostgreSQL"
    elif driver.startswith("mysql"):
        driver = "MariaDB"

    return f"{engine.url.database} ({driver})"


def header(text):
    app.console.print(f"\n[bold]{text}[/]\n")
