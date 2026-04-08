from pathlib import Path
from typing import Callable, Iterable

from macrostrat.database import Database

"""Higher-order functions that return a function that evaluates whether a condition is met on the database """
DbEvaluator = Callable[[Database], bool]

PathDependency = Callable[["Migration"], Path] | Path
DBCallable = Callable[[Database], None]


def column_type_is(
    schema: str, table: str, column: str, expected_type: str
) -> DbEvaluator:
    """
    Return a function that evaluates to True when the given column
    has the expected SQL type (e.g. 'integer', 'text').
    """

    def _check(db: Database) -> bool:
        if not db.inspector.has_table(table, schema=schema):
            return False
        cols = db.inspector.get_columns(table, schema=schema)
        for c in cols:
            if c["name"] == column:
                # Compile the SQLAlchemy type to its DB-specific SQL string, e.g. 'INTEGER', 'TEXT'
                col_type = c["type"].compile(dialect=db.engine.dialect)
                return col_type.lower() == expected_type.lower()
        # Column not found
        return False

    return _check


def exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema exists"""
    return lambda db: all(db.inspector.has_table(t, schema=schema) for t in table_names)


def not_exists(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema doesn't exist"""
    return _not(exists(schema, *table_names))


def schema_exists(schema: str) -> DbEvaluator:
    """Return a function that evaluates to true when the given schema exists"""
    return lambda db: db.inspector.has_schema(schema)


def view_exists(schema: str, *view_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given view in the given schema exists"""
    return lambda db: all(v in db.inspector.get_view_names(schema) for v in view_names)


def has_table_privilege(
    user: str, schema: str, table: str, privilege: str = "SELECT"
) -> DbEvaluator:
    """Return a function that evaluates to true when the given user has all specified privileges on the given table in the given schema"""

    def _has_priv(db: Database) -> bool:
        return db.run_query(
            "SELECT has_table_privilege(:user, :schema || '.' || :table, :privilege) AS has_privilege",
            dict(user=user, schema=schema, table=table, privilege=privilege),
        ).scalar()

    return _has_priv


def has_fks(schema: str, *table_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given table in the given schema has at least one foreign key"""
    return lambda db: all(
        db.inspector.has_table(t, schema=schema)
        and len(db.inspector.get_foreign_keys(t, schema=schema))
        for t in table_names
    )


def custom_type_exists(schema: str, *type_names: str) -> DbEvaluator:
    """Return a function that evaluates to true when every given custom type in the given schema exists"""
    return lambda db: all(db.inspector.has_type(t, schema=schema) for t in type_names)


def has_columns(schema: str, table: str, *fields: str, allow_view=False) -> DbEvaluator:
    """Return a function that evaluates to true when every given field in the given table exists"""

    def _has_fields(db: Database) -> bool:
        _has_table = db.inspector.has_table(table, schema=schema)
        if not _has_table and not allow_view:
            return False
        _has_view = table in db.inspector.get_view_names(schema)
        if not _has_table and not _has_view:
            return False
        columns = db.inspector.get_columns(table, schema=schema)
        col_names = [c["name"] for c in columns]
        return all(f in col_names for f in fields)

    return _has_fields


def _not(f: DbEvaluator) -> DbEvaluator:
    """Return a function that evaluates to true when the given function evaluates to false"""
    return lambda db: not f(db)


def _any(f: Iterable[DbEvaluator]) -> DbEvaluator:
    """Return a function that evaluates to true when any of the given functions evaluate to true"""

    def _any_f(db: Database) -> bool:
        return any(cond(db) for cond in f)

    return _any_f
