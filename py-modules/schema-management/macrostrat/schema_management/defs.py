import re
from contextlib import contextmanager
from pathlib import Path

from results.dbdiff.statements import check_for_drop
from results.schemainspect.pg import PostgreSQL
from results.schemainspect.pg.obj import PROPS
from rich import print
from sqlalchemy import TextClause, text

from macrostrat.core.config import settings
from macrostrat.database import Database
from macrostrat.dinosaur.cluster import database_cluster
from macrostrat.utils.logs import get_logger, suppress_loggers

from .composer import build_schema

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


def apply_schema_for_environment(
    db: Database,
    env: str,
    *,
    statement_filter=None,
    transform_statement=None,
    suppress_logging: bool = True,
    target: str | None = None,
    chunks=None,
):
    """Build the declarative schema for ``env``.

    :param target: a subsystem (chunk) name; when given, only that chunk and its
        transitive dependencies are applied. When omitted, the full schema for
        the environment is built.
    :param chunks: a pre-resolved chunk list (e.g. from ``selected_chunks``);
        takes precedence over ``target``.
    """
    _suppressed_loggers = []
    if suppress_logging:
        _suppressed_loggers = ["sqlalchemy.engine", "macrostrat.database.query"]

    with suppress_loggers(*_suppressed_loggers):
        build_schema(
            db,
            env,
            chunks,
            transform_statement=transform_statement,
            statement_filter=statement_filter,
            target=target,
        )
    return db


@contextmanager
def temporary_database_cluster(**kwargs):
    """Context manager to create a temporary database cluster"""
    image_tag = kwargs.pop("image", "macrostrat.local/database:latest")
    build_context = kwargs.pop("context", settings.srcroot / "base-images" / "database")
    optimize_for_testing = kwargs.pop("optimize", True)
    config = {
        "shared_preload_libraries": "pgaudit,pg_stat_statements",
    }

    with database_cluster(
        image_tag,
        context=build_context,
        optimize_for_testing=optimize_for_testing,
        config=config,
        **kwargs,
    ) as db:
        yield db


@contextmanager
def planning_database(environment, **kwargs):
    """Context manager to create a temporary database for planning schema changes"""
    # Spin up an image with this container
    with temporary_database_cluster(**kwargs) as plan_db:
        apply_schema_for_environment(plan_db, environment)
        yield plan_db


# Each of these catalog queries skips system schemas with a `not in (…)` list
# holding this pair, which other schemas can be added to.
SYSTEM_SCHEMAS = "'information_schema', 'pg_toast'"
SCHEMA_FILTERED_QUERIES = (
    "ALL_RELATIONS_QUERY",
    "COLLATIONS_QUERY",
    "CONSTRAINTS_QUERY",
    # Both ends of a dependency, so none names an object left unloaded.
    "DEPS_QUERY",
    "ENUMS_QUERY",
    "FUNCTIONS_QUERY",
    "INDEXES_QUERY",
    "PRIVILEGES_QUERY",
    "SCHEMAS_QUERY",
    "SEQUENCES_QUERY",
)


# schemainspect finds the owner in `pg_tables`, which lacks views, so view grants vanished.
PRIVILEGES_QUERY = f"""
select
  g.table_schema as schema,
  g.table_name as name,
  'table' as object_type,
  g.grantee as user,
  g.privilege_type as privilege
from information_schema.role_table_grants g
join pg_catalog.pg_namespace n on n.nspname = g.table_schema
join pg_catalog.pg_class c on c.relnamespace = n.oid and c.relname = g.table_name
where g.grantee <> pg_catalog.pg_get_userbyid(c.relowner)
  and g.table_schema not in ('pg_internal', 'pg_catalog', {SYSTEM_SCHEMAS})
  and g.table_schema not like 'pg_temp_%' and g.table_schema not like 'pg_toast_temp_%'
order by schema, name, user
"""


def _add_to_system_schemas(query, names: str):
    # Over a SQLAlchemy connection, the inspector's queries are `text()` clauses.
    if isinstance(query, TextClause):
        return text(_add_to_system_schemas(query.text, names))
    return query.replace(SYSTEM_SCHEMAS, f"{SYSTEM_SCHEMAS}, {names}")


class OurPostgreSQL(PostgreSQL):
    included_schemas = ["public"]

    def __init__(self, conn, schemas=None):
        # Read by `load_all`, which the parent constructor calls.
        if schemas is not None:
            self.included_schemas = schemas
        super().__init__(conn)

    def load_all(self):
        # Large unmanaged schemas (`sources`) dominate the catalog; never read them.
        query = (
            "SELECT nspname FROM pg_catalog.pg_namespace"
            " WHERE nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema'"
        )
        if self.connection_type == "sqlalchemy":
            query = text(query)
        present = [r.nspname for r in self.execute(query)]
        self.PRIVILEGES_QUERY = PRIVILEGES_QUERY
        if self.connection_type == "sqlalchemy":
            self.PRIVILEGES_QUERY = text(PRIVILEGES_QUERY)
        self.exclude_schemas([s for s in present if s not in self.included_schemas])
        super().load_all()

    def exclude_schemas(self, schemas):
        if not schemas:
            return
        names = ", ".join("'" + s.replace("'", "''") + "'" for s in schemas)
        for attr in SCHEMA_FILTERED_QUERIES:
            setattr(self, attr, _add_to_system_schemas(getattr(self, attr), names))

    def filter_schema(self, schema=None, exclude_schema=None):
        for prop in PROPS.split():
            att = getattr(self, prop)
            filtered = {
                k: v for k, v in att.items() if v.schema in self.included_schemas
            }
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


_ROLE_STATEMENT = re.compile(r"\s*(SET|RESET)\s+ROLE\b", re.IGNORECASE)


class StatementCounter:
    def __init__(self, safe: bool = True):
        self.total = 0
        self.unsafe = 0
        self.safe = safe
        self.statements = []

    def filter(self, s, params):
        # The plan's own `SET ROLE` / `RESET ROLE`, for applying it by hand: `apply`
        # manages the role itself (`applied_as_app_owner`), and they are not changes.
        if _ROLE_STATEMENT.match(s):
            return False
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
