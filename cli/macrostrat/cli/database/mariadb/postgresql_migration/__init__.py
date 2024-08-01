from pathlib import Path
from textwrap import dedent

from macrostrat.database import database_exists, create_database, drop_database
from macrostrat.database.utils import run_sql
from macrostrat.utils import get_logger
from macrostrat.utils.shell import run
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.engine import Engine
from macrostrat.core.config import settings
from macrostrat.core import app
from .db_changes import get_data_counts_maria, get_data_counts_pg, compare_data_counts, find_row_variances, find_col_variances
from ..restore import copy_mariadb_database
from ..utils import mariadb_engine
from ..._legacy import get_db
from ...utils import docker_internal_url
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
    temp_db_name = maria_engine.url.database + "_temp"
    maria_temp_engine = create_engine(maria_engine.url.set(database=temp_db_name))
    #pg_temp_engine = create_engine(pg_engine.url.set(database=temp_db_name))
    pg_temp_engine = create_engine(pg_engine.url.set(database=temp_db_name))

    steps: set[MariaDBMigrationStep] = _all_steps
    if step is not None and len(step) > 0:
        steps = set(step)

    if MariaDBMigrationStep.COPY_MARIADB in steps:
        copy_mariadb_database(maria_engine, maria_temp_engine, overwrite=overwrite)

    if MariaDBMigrationStep.PGLOADER in steps:
        pgloader_pre_script(maria_temp_engine)
        pgloader(maria_temp_engine, pg_temp_engine, overwrite=overwrite)
        pgloader_post_script(pg_temp_engine)

    if MariaDBMigrationStep.CHECK_DATA in steps:
        should_proceed = compare_row_counts(maria_engine, pg_temp_engine, pg_engine)
        find_row_col_variances(pg_engine)
        if not should_proceed:
            raise ValueError("Data comparison failed. Aborting migration.")

    if MariaDBMigrationStep.FINALIZE in steps:
        raise NotImplementedError("Copy to Macrostrat database not yet implemented")


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
        raw_database_url(docker_internal_url(dest.url))+"?sslmode=prefer",

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

def find_row_col_variances(pg_engine: Engine):
    tables = ['col_refs',
    'lookup_unit_attrs_api',
    'lookup_unit_intervals',
    'strat_names_meta',
    'sections',
    'unit_econs',
    'lookup_strat_names',
    'measures',
    'projects',
    'timescales',
    'strat_tree',
    'refs',
    'unit_liths',
    'lookup_units',
    'measurements',
    'units',
    'autocomplete',
    'col_areas',
    'unit_strat_names',
    'unit_environs',
    'cols',
    'intervals',
    'lith_atts',
    'timescales_intervals',
    'unit_boundaries',
    'econs',
    'environs',
    'units_sections',
    'unit_measures',
    'strat_names',
    'lookup_unit_liths',
    'liths',
    'concepts_places',
    'strat_names_places',
    'col_groups',
    'measuremeta',
    'places']
    find_row_variances(
        pg_engine.url.database, pg_engine.url.database, "macrostrat_temp", pg_engine.url.username, pg_engine.url.password, tables,
        pg_engine
    )
    find_col_variances(
        pg_engine.url.database, pg_engine.url.database, "macrostrat_temp", pg_engine.url.username, pg_engine.url.password, tables,
        pg_engine
    )



def db_identifier(engine: Engine):
    driver = engine.url.drivername
    if driver.startswith("postgresql"):
        driver = "PostgreSQL"
    elif driver.startswith("mysql"):
        driver = "MariaDB"

    return f"{engine.url.database} ({driver})"


def header(text):
    app.console.print(f"\n[bold]{text}[/]\n")
