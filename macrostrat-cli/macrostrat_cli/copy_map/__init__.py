"""A command to copy a macrostrat source from one database to another.
This should really be part of the map-integration package, but it's here
on a temporary basis.
"""

from typer import Option
from macrostrat.database import Database
from macrostrat.database.postgresql import table_exists, on_conflict
from psycopg2.sql import Identifier
from sqlalchemy.dialects.postgresql import insert
from .._dev.transfer_tables import transfer_tables


def copy_macrostrat_sources(
    slug: str,
    from_db: str = Option(None, "--from"),
    to_db: str = Option(None, "--to"),
    message: str = Option(None, "--message"),
    replace: bool = False,
):
    """Copy a macrostrat source from one database to another."""

    from ..database import get_db
    from macrostrat.database import Database

    if from_db is None and to_db is None:
        raise ValueError("Must specify either --from or --to")

    _db = get_db()
    if from_db is None:
        from_db = _db
    else:
        from_db = Database(_db.engine.url.set(database=from_db))

    if to_db is None:
        to_db = get_db()
    else:
        to_db = Database(_db.engine.url.set(database=to_db))

    from_db.automap(schemas=["maps", "macrostrat_auth"])
    # Add the source to the new database
    to_db.automap(schemas=["maps", "macrostrat_auth"])

    # Copy the source
    copy_macrostrat_source(from_db, to_db, slug, message=message, replace=replace)


def copy_macrostrat_source(
    from_db: Database, to_db: Database, slug: str, message: str, replace: bool
):
    tables = [
        Identifier("sources", slug + "_" + dtype)
        for dtype in ["points", "lines", "polygons"]
    ]

    if replace:
        # Delete the tables if they exist
        for table in tables:
            to_db.run_sql("DROP TABLE IF EXISTS {table}", params=dict(table=table))

    # Copy the sources record
    old_source_id, new_source_id = copy_sources_record(
        from_db, to_db, slug, replace=replace
    )

    # Copy the tables
    transfer_tables(
        from_database=from_db.engine,
        to_database=to_db.engine,
        tables=[".".join(t.strings) for t in tables],
    )

    for table in tables:
        (schema, name) = table.strings
        if not table_exists(to_db, name, schema=schema):
            continue

        to_db.run_sql(
            """
            UPDATE {table} SET source_id = :source_id;
            ALTER TABLE {table} ADD FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);
            """,
            params=dict(source_id=new_source_id, table=table),
        )

    # Create an entry in the operations log
    log_map_operation(
        to_db,
        source_id=new_source_id,
        comments=message,
        details=dict(
            slug=slug, src_database=str(from_db.engine.url), src_source_id=old_source_id
        ),
    )

    try:
        copy_operations_from_src_database(from_db, to_db, old_source_id, new_source_id)
    except Exception as err:
        raise MacrostratCommandError(err, "Could not copy operations log")


def log_map_operation(
    db: Database,
    **kwargs,
):
    Operation = db.model.maps_source_operations
    op = Operation(operation="get-source", app="macrostrat-cli", **kwargs)
    db.session.add(op)
    db.session.commit()


def copy_operations_from_src_database(
    from_db: Database, to_db: Database, old_source_id: int, new_source_id: int
):
    """
    Copy the operations log from one database to another.
    """

    Operation = to_db.model.maps_source_operations

    # Sometimes the source isn't necessarily going to have an operations table
    src_Operation = getattr(from_db.model, "maps_source_operations", None)
    if src_Operation is not None:
        # Get source operations
        src_ops = from_db.session.query(src_Operation).filter_by(
            source_id=old_source_id
        )
        for src_op in src_ops:
            op = Operation(
                source_id=new_source_id,
                app=src_op.app,
                operation=src_op.operation,
                comments=src_op.comments,
                details=dict(
                    src_database=str(from_db.engine.url),
                    src_source_id=src_op.source_id,
                    src_user_id=src_op.user_id,
                    **src_op.details,
                ),
                date=src_op.date,
            )
            to_db.session.add(op)
        to_db.session.commit()


def copy_sources_record(from_db: Database, to_db: Database, slug: str, replace=False):
    """Copy a maps.sources record from one database to another."""

    Sources = from_db.model.maps_sources

    source = from_db.session.query(Sources).filter_by(slug=slug).one_or_none()
    if source is None:
        raise ValueError(f"Source {slug} not found in {from_db.engine.url.database}")

    Sources2 = to_db.model.maps_sources

    source_vals = source.__dict__
    old_source_id = source_vals.pop("source_id")
    del source_vals["_sa_instance_state"]

    query = insert(Sources2.__table__).values(source_vals)

    if replace:
        # Update the source_id with on_conflict_do_update
        vals = {
            name: value for name, value in source_vals.items() if name not in ["slug"]
        }

        query = query.on_conflict_do_update(
            index_elements=["slug"],
            set_=vals,
        )

    with on_conflict("restrict"):
        new_source_id = to_db.session.execute(
            query.returning(Sources2.source_id)
        ).scalar()

    # Get the new source_id
    print("Added source to new database with ID", new_source_id)
    return old_source_id, new_source_id


class MacrostratCommandError(Exception):
    base_error: Exception
    description: str

    def init(self, base_error: Exception, description: str):
        self.base_error = base_error
        self.description = description
