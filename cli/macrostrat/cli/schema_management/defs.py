from contextlib import contextmanager

import docker
from results.dbdiff.statements import check_for_drop
from results.schemainspect.pg import PostgreSQL
from results.schemainspect.pg.obj import PROPS
from rich import print

from macrostrat.core.config import settings
from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster.utils import database_cluster


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


def apply_schema_for_environment(
    db: Database, env: str, *, recursive: bool = True, statement_filter=None
):
    for env_dir in schema_dirs_for_environment(env):
        schema_dir = env_dir
        if not schema_dir.exists():
            continue
        fixtures = sorted(list(schema_dir.glob("*.sql")))
        fixtures = [f for f in fixtures if not f.name.endswith(".plan.sql")]

        if len(fixtures) == 0:
            continue
        db.run_fixtures(fixtures, recursive=recursive, statement_filter=filter)


@contextmanager
def planning_database(environment):
    """Context manager to create a temporary database for planning schema changes"""
    client = docker.from_env()

    img_root = settings.srcroot / "base-images" / "database"

    # Build postgres pgaudit image
    img_tag = "macrostrat.local/database:latest"

    client.images.build(path=str(img_root), tag=img_tag)

    # Spin up an image with this container
    port = 54884
    with database_cluster(client, img_tag, port=port) as container:
        _url = f"postgresql://postgres@localhost:{port}/postgres"
        plan_db = Database(_url)

        # Optimize postgres for fast testing
        # TODO: this must be integrated with the database_cluster context manager
        plan_db.run_sql(
            """
            SET fsync TO off;
            SET synchronous_commit TO off;
            SET full_page_writes TO off;
            SET temp_buffers TO '16MB';
            SET work_mem TO '64MB';
            SET maintenance_work_mem TO '128MB';
            SET autovacuum TO off;
        """
        )

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
