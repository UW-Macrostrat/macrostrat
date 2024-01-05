from typer import Option
from macrostrat.database import Database
from macrostrat.database.postgresql import table_exists
from .._dev.transfer_tables import transfer_tables


def copy_macrostrat_source(
    slug: str,
    from_db: str = Option(None, "--from"),
    to_db: str = Option(None, "--to"),
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

    tables = [
        f"sources.{slug}_points",
        f"sources.{slug}_lines",
        f"sources.{slug}_polygons",
    ]

    if replace:
        # Delete the tables if they exist
        for table in tables:
            base_table = table.split(".")[1]
            if not table_exists(to_db, base_table, "sources"):
                continue

            to_db.run_sql(f"DROP TABLE IF EXISTS {table};")

    # Copy the sources record
    source_id = copy_sources_record(from_db, to_db, slug, replace=replace)

    # Copy the tables
    transfer_tables(
        from_database=from_db.engine,
        to_database=to_db.engine,
        tables=tables,
    )

    for table in tables:
        base_table = table.split(".")[1]
        if not table_exists(to_db, base_table, "sources"):
            continue

        to_db.run_sql(
            f"""
            UPDATE {table} SET source_id = :source_id;
            ALTER TABLE {table} ADD FOREIGN KEY (source_id) REFERENCES maps.sources (source_id);
            """,
            params=dict(source_id=source_id),
        )


def copy_sources_record(from_db: Database, to_db: Database, slug: str, replace=False):
    """Copy a macrostrat sources record from one database to another."""

    from_db.automap(schemas=["maps"])
    Sources = from_db.model.maps_sources

    source = from_db.session.query(Sources).filter_by(slug=slug).one_or_none()
    if source is None:
        raise ValueError(f"Source {slug} not found in {from_db.engine.url.database}")

    # Add the source to the new database
    to_db.automap(schemas=["maps"])
    Sources2 = to_db.model.maps_sources

    source_vals = source.__dict__
    del source_vals["source_id"]
    del source_vals["_sa_instance_state"]

    new_source = Sources2(**source_vals)

    if replace:
        to_db.session.query(Sources2).filter_by(slug=slug).delete()

    to_db.session.add(new_source)
    to_db.session.commit()

    # Get the new source_id
    print("Added source to new database with ID", new_source.source_id)
    return new_source.source_id
