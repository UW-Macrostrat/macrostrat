from contextlib import contextmanager

import docker
from macrostrat.database import Database
from macrostrat.dinosaur.upgrade_cluster.utils import database_cluster
from psycopg2.sql import Identifier
from results.dbdiff.statements import check_for_drop
from results.schemainspect.pg import PostgreSQL
from results.schemainspect.pg.obj import PROPS
from rich import print

from macrostrat.core.config import settings

# First, register all migrations
# NOTE: right now, this is quite implicit.

managed_schemas = [
    "public",
    "macrostrat",
    "macrostrat_auth",
    "ecosystem",
    "storage",
    "maps",
    "maps_metadata",
    "lines",
    "carto",
    "carto_new",
    "user_features",
    "usage_stats",
    "integrations",
    "macrostrat_xdd",
    "macrostrat_api",
]


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


def plan_schema_for_environment(env: str, db: Database):
    # Set up roles
    for role in [
        "macrostrat_admin",
        "macrostrat",
        "web_admin",
        "web_user",
        "web_anon",
    ]:
        db.run_sql("CREATE ROLE {role}", dict(role=Identifier(role)))

    schema_dir = settings.srcroot / "schema" / "local"

    db.run_fixtures(schema_dir)


@contextmanager
def planning_database():
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
        plan_schema_for_environment("local", plan_db)
        yield plan_db


class OurPostgreSQL(PostgreSQL):
    def filter_schema(self, schema=None, exclude_schema=None):
        def is_managed_schema(x):
            return x.schema in managed_schemas

        comparator = is_managed_schema

        for prop in PROPS.split():
            att = getattr(self, prop)
            filtered = {k: v for k, v in att.items() if comparator(v)}
            setattr(self, prop, filtered)


def get_inspector(x):
    if hasattr(x, "url") and hasattr(x, "URL"):
        with x.t() as t:
            inspected = OurPostgreSQL(t.c)
    else:
        try:
            inspected = OurPostgreSQL(x.c)
        except AttributeError:
            inspected = OurPostgreSQL(x)
    inspected.filter_schema()
    return inspected


class StatementCounter:
    def __init__(self, safe: bool = True):
        self.total = 0
        self.unsafe = 0
        self.safe = safe

    def filter(self, s, params):
        self.total += 1
        if is_unsafe_statement(s):
            self.unsafe += 1
            if self.safe:
                return False
        return True

    def print_report(self):
        applied_count = self.total
        _unsafe_action = "applied"
        if self.safe:
            applied_count -= self.unsafe
            _unsafe_action = "skipped"

        print(f"[dim]{applied_count} changes applied")
        if self.unsafe > 0:
            print(f"[red bold]{self.unsafe} unsafe changes were {_unsafe_action}")
