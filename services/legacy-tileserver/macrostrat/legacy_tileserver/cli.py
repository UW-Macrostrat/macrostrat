from pathlib import Path

from macrostrat.utils import relative_path
from typer import Typer

here = relative_path(__file__)
root = (here).resolve()


# App
_cli = Typer(no_args_is_help=True, name="tileserver")


@_cli.command(name="create-mapnik-xml")
def create_mapnik_xml(outdir: Path):
    """Create image styles"""
    # Note: Carto NodeJS module must be installed globally for this to work

    from .image_tiles.mapnik_styles import make_mapnik_xml

    outdir.mkdir(parents=True, exist_ok=True)
    # This makes files without database connection information,
    # for testing purposes essentially
    for scale in ("large", "medium", "small", "tiny"):
        xml = make_mapnik_xml(scale)
        with (outdir / f"{scale}.xml").open("w") as f:
            f.write(xml)
