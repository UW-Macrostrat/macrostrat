from rich import print
from typer import Option

from macrostrat.core import app


def update_schema(
    match: str = Option(None),
    subsystems: list[str] = Option(None),
    _all: bool = Option(None, "--all"),
):
    """DEPRECATED: Update the database schema

    Now this is handled by migrations and schema diffing.
    """
    from macrostrat.core.config import PG_DATABASE
    from macrostrat.database import Database

    db_subsystem = app.subsystems.get("database")

    if subsystems is None:
        subsystems = []

    """Create schema additions"""
    schema_dir = fixtures_dir
    # Loaded from env file
    db = Database(PG_DATABASE)

    if match is not None and len(subsystems) == 0:
        # core is implicit
        subsystems = ["core"]

    if not _all and len(subsystems) == 0:
        print("Please specify --all or --subsystems to update the schema")
        print("Available subsystems:")
        for hunk in db_subsystem.schema_hunks:
            print(f"  {hunk.name}")
        return

    # Run subsystem updates
    for hunk in db_subsystem.schema_hunks:
        if (
            subsystems is not None
            and len(subsystems) != 0
            and hunk.name not in subsystems
        ):
            continue
        hunk.apply(db, match=match)

    app.subsystems.run_hook("schema-update")
