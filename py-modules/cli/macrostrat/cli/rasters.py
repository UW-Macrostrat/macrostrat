"""Raster data management.

The registration surface comes wholesale from `macrostrat.raster_index`, mounted
against Macrostrat's own database configuration. The only thing added here is the
legacy COG-conversion command from the prototype `macrostrat.raster_cli`, kept as
a deprecated subcommand while its replacement is worked out.
"""

from typer import Typer

from macrostrat.core.exc import MacrostratError

__all__ = ["build_raster_cli"]


def build_raster_cli() -> Typer:
    """The `macrostrat raster` command group.

    Raises `ImportError` if `macrostrat.raster_index` isn't installed, so the
    entrypoint can carry on without the subsystem — the raster libraries are
    still developed against local checkouts.
    """
    from macrostrat.raster_index.cli import cli, set_default_connection

    # Point the index CLI at Macrostrat's configured database, so its users
    # never have to pass `--database` (which still works, and still wins).
    set_default_connection(_database_url)

    _add_legacy_commands(cli)
    return cli


def _database_url() -> str:
    """Resolved per command, not at import, so a missing URL isn't fatal here."""
    from macrostrat.core.config import settings

    url = getattr(settings, "pg_database", None)
    if url is None:
        raise MacrostratError("No database URL found in settings")
    return url


def _add_legacy_commands(cli: Typer) -> None:
    """Mount the prototype COG-conversion command, if it's installed.

    `macrostrat.raster_cli` predates the index and only knows how to convert an
    image to a COG and push it to S3. That step still has to happen somewhere;
    until it has a real home, it stays reachable and marked deprecated.
    """
    try:
        from macrostrat.raster_cli.process import process_image
    except ImportError:
        return

    @cli.command(name="process", deprecated=True)
    def _process_image(image: str, key: str = None):
        """Convert an image to a COG and upload it to S3."""
        process_image(image, key)
