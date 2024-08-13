from pathlib import Path
from textwrap import dedent

from macrostrat.database import database_exists, create_database, drop_database
from macrostrat.database.utils import run_sql, run_query
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.engine import Engine, make_url
from macrostrat.core.config import settings
from macrostrat.core import app
from .db_changes import (
    get_data_counts_maria,
    get_data_counts_pg,
    compare_data_counts,
    find_row_variances,
    find_col_variances,
)
from psycopg2.sql import Identifier
from ..restore import copy_mariadb_database
from ..utils import mariadb_engine
from ..._legacy import get_db
from ...utils import docker_internal_url, pg_temp_user
from ...._dev.utils import raw_database_url

__here__ = Path(__file__).parent

log = get_logger(__name__)

from enum import Enum


class MariaDBMigrationStep(Enum):
    COPY_MARIADB = "copy-mariadb"
    PGLOADER = "pgloader"
    CHECK_DATA = "check-data"
    FINALIZE = "finalize"


_all_steps = {
    MariaDBMigrationStep.COPY_MARIADB,
    MariaDBMigrationStep.PGLOADER,
    MariaDBMigrationStep.CHECK_DATA,
    MariaDBMigrationStep.FINALIZE,
}


def migrate_mariadb_to_postgresql(
    overwrite: bool = False, step: list[MariaDBMigrationStep] = None
):
    """Migrate the legacy Macrostrat database from MariaDB to PostgreSQL."""

    # Get the default MariaDB and PostgreSQL engines from the Macrostrat app's
    # configuration (macrostrat.toml).
    maria_engine = mariadb_engine()
    pg_engine = get_db().engine
    temp_db_name = "macrostrat_temp"
    maria_temp_engine = create_engine(maria_engine.url.set(database=temp_db_name))
    #pg_temp_engine = create_engine(make_url(settings.pgloader_target_database))

    # Destination schemas in the PostgreSQL database
    temp_schema = temp_db_name
    final_schema = "macrostrat"

    steps: set[MariaDBMigrationStep] = _all_steps
    if step is not None and len(step) > 0:
        steps = set(step)

    if MariaDBMigrationStep.COPY_MARIADB in steps:
        copy_mariadb_database(maria_engine, maria_temp_engine, overwrite=overwrite)

    if MariaDBMigrationStep.PGLOADER in steps:
        pgloader(maria_temp_engine, pg_engine, temp_schema, overwrite=overwrite)

    if MariaDBMigrationStep.CHECK_DATA in steps:
        # NOTE: the temp schema and the final schema must be provided
        should_proceed = compare_row_counts(maria_temp_engine, pg_engine, temp_schema)
        if should_proceed:
            raise ValueError("Data comparison failed. Aborting migration.")
        else:
            print("check-data completed!")


    if MariaDBMigrationStep.FINALIZE in steps:
        should_proceed = preserve_macrostrat_data(pg_engine)
        if should_proceed:
            raise NotImplementedError("Copy to macrostrat schema not yet implemented")
        else:
            print("finalize completed!")

def pgloader(source: Engine, dest: Engine, target_schema: str, overwrite: bool = False):
    _build_pgloader()

    if target_schema != source.url.database:
        raise ValueError(
            "The target schema must be the same as the source database name"
        )

    pgloader_pre_script(source)
    _schema = Identifier(target_schema)

    if overwrite:
        run_sql(
            dest,
            """
            DROP SCHEMA IF EXISTS {schema} CASCADE;
            CREATE SCHEMA {schema};
            """,
            dict(schema=_schema),
        )

    username = "maria_migrate"
    with pg_temp_user(dest, username, overwrite=overwrite) as pg_temp:
        # Create a temporary user that PGLoader can use to connect to the PostgreSQL database
        # and create the temporary schema.
        run_sql(
            dest,
            "GRANT ALL PRIVILEGES ON SCHEMA {schema} TO {user}",
            dict(
                schema=_schema,
                user=Identifier(username),
            ),
        )
        _run_pgloader(source, pg_temp)
        pgloader_post_script(pg_temp)


def schema_exists(engine: Engine, schema: str):
    return run_query(
        engine,
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema_name",
        dict(schema=schema),
    ).scalar()


def pgloader_pre_script(engine: Engine):
    assert engine.url.drivername.startswith("mysql")
    pre_script = __here__ / "pgloader-pre-script.sql"
    run_sql(engine, pre_script)


def pgloader_post_script(engine: Engine):
    app.console.print("\n[bold]Running post-migration script[/]")
    assert engine.url.drivername.startswith("postgres")
    post_script = __here__ / "pgloader-post-script.sql"
    run_sql(engine, post_script)


def _run_pgloader(source: Engine, dest: Engine):
    """
    Command terminal to run pgloader. Ensure Docker app is running.
    """
    db_exists = database_exists(dest.url)
    if not db_exists:
        header("Creating PostgreSQL database")
        create_database(dest.url)

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
        raw_database_url(docker_internal_url(dest.url)) + "?sslmode=prefer",
    )


def _build_pgloader():
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


def compare_row_counts(maria: Engine, pg_engine: Engine, schema):

    console = app.console

    maria_rows, maria_columns = get_data_counts_maria(maria)
    pg_macrostrat_temp_rows, pg_macrostrat_temp_columns = get_data_counts_pg(
        pg_engine, schema
    )

    db1 = db_identifier(maria)
    db2 = schema
    db3 = db_identifier(pg_engine)

    header(f"\n\nComparing [cyan]{db1}[/] to [cyan]{db2}[/].")

    row_variance, column_variance = compare_data_counts(
        maria_rows,
        pg_macrostrat_temp_rows,
        maria_columns,
        pg_macrostrat_temp_columns,
        db1,
        db2,
    )

    pg_rows, pg_columns = get_data_counts_pg(pg_engine, "macrostrat")

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

    tables = [
        "col_refs",
        "lookup_unit_attrs_api",
        "lookup_unit_intervals",
        "strat_names_meta",
        "sections",
        "unit_econs",
        "lookup_strat_names",
        "measures",
        "projects",
        "timescales",
        "strat_tree",
        "refs",
        "unit_liths",
        "lookup_units",
        "measurements",
        "units",
        "autocomplete",
        "col_areas",
        "unit_strat_names",
        "unit_environs",
        "cols",
        "intervals",
        "lith_atts",
        "timescales_intervals",
        "unit_boundaries",
        "econs",
        "environs",
        "units_sections",
        "unit_measures",
        "strat_names",
        "lookup_unit_liths",
        "liths",
        "concepts_places",
        "strat_names_places",
        "col_groups",
        "measuremeta",
        "places",
    ]
    find_row_variances(
        pg_engine.url.database,
        pg_engine.url.database,
        "macrostrat_temp",
        pg_engine.url.username,
        pg_engine.url.password,
        tables,
        pg_engine,
    )
    find_col_variances(
        pg_engine.url.database,
        pg_engine.url.database,
        "macrostrat_temp",
        pg_engine.url.username,
        pg_engine.url.password,
        tables,
        pg_engine,
    )

def preserve_macrostrat_data(engine: Engine):
    app.console.print("\n[bold]Running script[/]")
    assert engine.url.drivername.startswith("postgres")
    preserve_data = __here__ / "preserve-macrostrat-data.sql"
    run_sql(engine, preserve_data)

def db_identifier(engine: Engine):
    driver = engine.url.drivername
    if driver.startswith("postgresql"):
        driver = "PostgreSQL"
    elif driver.startswith("mysql"):
        driver = "MariaDB"

    return f"{engine.url.database} ({driver})"


def header(text):
    app.console.print(f"\n[bold]{text}[/]\n")
