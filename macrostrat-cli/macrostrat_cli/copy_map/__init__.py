from typer import Option


def copy_macrostrat_source(
    slug: str, from_db: str = Option(None, "--from"), to_db: str = Option(None, "--to")
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

    # Copy the sources record
    from_db.automap(schemas=["public", "maps"])
    # Sources = from_db.model.maps_sources

    import IPython

    IPython.embed()
