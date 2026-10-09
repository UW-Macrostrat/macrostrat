import ast
import inspect
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.types import UserDefinedType

from macrostrat.database import Database


class TopoGeometry(UserDefinedType):
    """PostGIS `topogeometry`, which SQLAlchemy's Postgres dialect doesn't know.

    Reflection is otherwise fine — the column just comes back as `NullType` with a
    `SAWarning` per column per inspection, which is noise on every migration check
    that touches `map_bounds`. Registering the name resolves it. Nothing here
    composes topogeometry values; this only needs to be a distinct, nameable type.
    """

    cache_ok = True

    def get_col_spec(self, **kw):
        return "topogeometry"


ischema_names["topogeometry"] = TopoGeometry

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


def has_schema(schema: str) -> DbEvaluator:
    """Return a function that evaluates to true when the given schema exists"""
    return lambda db: db.inspector.has_schema(schema)


def _not(f: DbEvaluator) -> DbEvaluator:
    """Return a function that evaluates to true when the given function evaluates to false"""
    return lambda db: not f(db)


def _any(f: Iterable[DbEvaluator]) -> DbEvaluator:
    """Return a function that evaluates to true when any of the given functions evaluate to true"""
    # Callers pass generators, which a second evaluation would find exhausted
    f = list(f)

    def _any_f(db: Database) -> bool:
        return any(cond(db) for cond in f)

    return _any_f


def describe_condition(cond: DbEvaluator) -> str:
    """Render a condition on one line, to explain why a migration cannot apply.

    A closure built by a factory such as `exists` reads as the factory call that
    built it, a lambda as its source, and a named function as its name and the
    first line of its docstring.
    """
    scopes = getattr(cond, "__qualname__", "").split(".<locals>.")
    # A method's scope is dotted; its lambdas read better as source
    if len(scopes) > 1 and "." not in scopes[-2] and cond.__closure__:
        return _factory_call(cond, scopes[-2])
    name = getattr(cond, "__name__", None)
    if name == "<lambda>":
        return _lambda_body(cond) or name
    if name is None:
        return _shorten(repr(cond))
    doc = inspect.getdoc(cond)
    if doc:
        return f"{name}: {_shorten(doc.split(chr(10) * 2)[0])}"
    return name


def _factory_call(cond: DbEvaluator, factory_name: str) -> str:
    values = {}
    for var, cell in zip(cond.__code__.co_freevars, cond.__closure__):
        try:
            values[var] = cell.cell_contents
        except ValueError:
            continue
    try:
        params = inspect.signature(cond.__globals__[factory_name]).parameters
    except (KeyError, TypeError, ValueError):
        params = None
    if params is None:
        args = [f"{k}={_describe_value(v)}" for k, v in values.items()]
        return f"{factory_name}({', '.join(args)})"

    args = []
    for param in params.values():
        if param.name not in values:
            continue
        value = values[param.name]
        if param.kind == param.VAR_POSITIONAL:
            args.extend(_describe_value(v) for v in value)
        elif param.default is param.empty:
            args.append(_describe_value(value))
        elif value != param.default:
            args.append(f"{param.name}={_describe_value(value)}")
    return f"{factory_name}({', '.join(args)})"


def _describe_value(value) -> str:
    if callable(value):
        return describe_condition(value)
    if isinstance(value, (list, tuple)) and any(callable(v) for v in value):
        return "[" + ", ".join(_describe_value(v) for v in value) + "]"
    if isinstance(value, str):
        value = " ".join(value.split())
    return _shorten(repr(value))


def _lambda_body(fn) -> str | None:
    try:
        source, tree = _parsed_source(inspect.getsourcefile(fn))
    except (OSError, TypeError, SyntaxError):
        return None
    line = fn.__code__.co_firstlineno
    lambdas = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Lambda) and node.lineno == line
    ]
    if not lambdas:
        return None
    first = min(lambdas, key=lambda node: node.col_offset)
    return _shorten(ast.get_source_segment(source, first.body))


@lru_cache(64)
def _parsed_source(path: str) -> tuple[str, ast.Module]:
    source = Path(path).read_text()
    return source, ast.parse(source)


def _shorten(text: str, width: int = 140) -> str:
    text = " ".join(text.split())
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"
