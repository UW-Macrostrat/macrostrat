from contextlib import contextmanager

import docker
from results.dbdiff.statements import check_for_drop
from results.schemainspect.pg import PostgreSQL
from results.schemainspect.pg.obj import PROPS
from rich import print

from macrostrat.core.config import settings
from macrostrat.database import Database
from macrostrat.utils import get_logger

import logging
from contextlib import contextmanager
from testcontainers.postgres import PostgresContainer

log = get_logger(__name__)


def is_unsafe_statement(s: str) -> bool:
    """Check if a SQL statement is unsafe (i.e., contains DROP)"""
    is_drop = check_for_drop(s)
    if not is_drop:
        return False
    allowed_drops = [
        "drop view",
        "drop index",
        "drop function",
        "drop trigger",
    ]
    s_lower = s.lower()
    for allowed in allowed_drops:
        if s_lower.startswith(allowed):
            return False
    return True


env_schema_dirs = {
    "local": ["production", "development"],
    "development": ["production"],
    "staging": ["production"],
    "production": ["production"],
}


def schema_dirs_for_environment(env: str):
    schema_dir = settings.srcroot / "schema"

    # Always apply the core schema
    yield schema_dir / "core"

    if env in ["development", "local"]:
        yield schema_dir / "development"

    if env in ["local"]:
        yield schema_dir / "local"


@contextmanager
def suppress_loggers(*loggers, level=logging.ERROR):
    """Temporarily suppresses logs for a specific logger or the root logger."""
    orig_level_map = {}
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        orig_level_map[logger_name] = logger.getEffectiveLevel()
        logger.setLevel(level)
    try:
        yield
    finally:
        for logger_name, original_level in orig_level_map.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(original_level)


def apply_schema_for_environment(
    db: Database,
    env: str,
    *,
    recursive: bool = True,
    statement_filter=lambda s, p: True,
    suppress_logging: bool = False,
    pattern: str = "*",
):
    if "*" not in pattern:
        pattern = f"*{pattern}*"

    for env_dir in schema_dirs_for_environment(env):
        schema_dir = env_dir
        if not schema_dir.exists():
            continue

        func = schema_dir.rglob if recursive else schema_dir.glob
        fixtures = sorted(list(func(pattern + ".sql")))
        fixtures = [f for f in fixtures if not f.name.endswith(".plan.sql")]

        if len(fixtures) == 0:
            continue
        _suppressed_loggers = []
        if suppress_logging:
            _suppressed_loggers = [
                "sqlalchemy.engine",
                "macrostrat.database.utils",
            ]
        with suppress_loggers(*_suppressed_loggers):
            db.run_fixtures(
                fixtures, recursive=recursive, statement_filter=statement_filter
            )


@contextmanager
def test_database_cluster(**kwargs):
    """Context manager to create a temporary database cluster"""
    should_build = kwargs.pop("build", False)
    image_tag = kwargs.pop("image", "macrostrat.local/database:latest")
    build_context = kwargs.pop("context", settings.srcroot / "base-images" / "database")
    optimize = kwargs.pop("optimize", True)
    driver = kwargs.pop("driver", None)

    if not optimize:
        should_build = True

    client = docker.from_env()
    # Check if image exists locally to avoid build
    if not should_build:
        try:
            client.images.get(image_tag)
            log.info(f"Using existing image {image_tag}")
        except docker.errors.ImageNotFound:
            should_build = True

    if should_build:
        # Build postgres pgaudit image
        client.images.build(path=str(build_context), tag=image_tag)

    container = PostgresContainer(image_tag, **kwargs)

    pg_config = {
        "shared_preload_libraries": "pgaudit,pg_stat_statements",
    }

    if optimize:
        pg_config = {
            **pg_config,
            "synchronous_commit": "off",
            "fsync": "off",
            "wal_level": "minimal",
            "max_wal_senders": "0",
            "full_page_writes": "off",
            "checkpoint_completion_target": "0.9",
        }
        container = container.with_kwargs(
            tmpfs={
                "/var/lib/postgresql/data": "rw",
            }
        ).with_env("POSTGRES_HOST_AUTH_METHOD", "trust")
    container = container.with_command(build_postgres_command(pg_config))
    container.start()
    try:
        _url = container.get_connection_url(driver=driver)
        db = Database(_url)
        yield db
    finally:
        container.stop()


def build_postgres_command(pg_config):
    cmd = "postgres"
    for k, v in pg_config.items():
        cmd += f" -c {k}={v}"
    return cmd


@contextmanager
def planning_database(environment, **kwargs):
    """Context manager to create a temporary database for planning schema changes"""
    # Spin up an image with this container
    with test_database_cluster(**kwargs) as plan_db:
        apply_schema_for_environment(plan_db, environment)
        yield plan_db


class OurPostgreSQL(PostgreSQL):
    included_schemas = ["public"]

    def __init__(self, conn, schemas=None):
        super().__init__(conn)
        if schemas is not None:
            self.included_schemas = schemas

    def filter_schema(self, schema=None, exclude_schema=None):
        def is_managed_schema(x):
            return x.schema in self.included_schemas

        comparator = is_managed_schema

        for prop in PROPS.split():
            att = getattr(self, prop)
            filtered = {k: v for k, v in att.items() if comparator(v)}
            setattr(self, prop, filtered)


def get_inspector(x, schemas=None):
    if hasattr(x, "url") and hasattr(x, "URL"):
        with x.t() as t:
            inspected = OurPostgreSQL(t.c, schemas)
    else:
        try:
            inspected = OurPostgreSQL(x.c, schemas)
        except AttributeError:
            inspected = OurPostgreSQL(x, schemas)
    inspected.filter_schema()
    return inspected


def get_all_schemas(db: Database, excluded_schemas=None):
    _excluded = [
        "information_schema",
        "pg_catalog",
        "pg_toast",
    ]
    if excluded_schemas is not None:
        _excluded.extend(excluded_schemas)
    return (
        db.run_query(
            """
        SELECT nspname AS schema_name FROM pg_catalog.pg_namespace
        WHERE NOT nspname = ANY(:excluded_schemas)
        AND nspname NOT LIKE 'pg_temp_%'
        AND nspname NOT LIKE 'pg_toast_%'
        """,
            {"excluded_schemas": _excluded},
        )
        .scalars()
        .all()
    )


class StatementCounter:
    def __init__(self, safe: bool = True):
        self.total = 0
        self.unsafe = 0
        self.safe = safe
        self.statements = []

    def filter(self, s, params):
        self.total += 1
        if is_unsafe_statement(s):
            self.unsafe += 1
            if self.safe:
                return False
        self.statements.append((s, params))
        return True

    def print_report(self, file=None, prefix=""):
        applied_count = self.total
        _unsafe_action = "applied"
        unsafe_suffix = ""
        if self.safe:
            applied_count -= self.unsafe
            _unsafe_action = "skipped"
        elif self.unsafe > 0:
            unsafe_suffix = f" ([red bold]{self.unsafe} unsafe[/])"

        n_text = _count(applied_count, "change")

        print(
            prefix + f"[dim]{n_text} applied" + unsafe_suffix,
            file=file,
        )
        if self.unsafe > 0 and self.safe:
            n_text = _count(self.unsafe, "unsafe change")
            print(
                prefix + f"[red bold]{n_text} skipped",
                file=file,
            )

    def schema_log_entries(self):
        return [s for s, p in self.statements if should_log_statement(s)]


def _count(count, label):
    plural = "" if count == 1 else "s"
    return f"{count} {label}{plural}"


def should_log_statement(s):
    """Filter out uninteresting statements for schema change logging"""
    s_lower = s.lower()
    uninteresting_starts = [
        "set",
        "notify",
        "alter role",
        "comment on",
        "create index",
        "drop index",
        "create view",
        "drop view",
        "create or replace view",
        "create or replace function",
        "create function",
        "drop function",
        "grant",
        "revoke",
    ]
    for start in uninteresting_starts:
        if s_lower.startswith(start + " "):
            return False
    return True
