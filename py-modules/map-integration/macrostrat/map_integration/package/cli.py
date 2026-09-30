"""Command-line entry points for map packages."""

from pathlib import Path
from sys import stdin
from typing import Annotated, Optional

from rich.console import Console
from rich.prompt import Prompt
from typer import Argument, Option

from macrostrat.core.exc import MacrostratError

from ..utils.map_info import MapExclude, MapState, complete_map_slugs

console = Console(stderr=True)


def export_command(
    output: Path = Argument(..., help="GeoPackage (.gpkg) to write"),
    maps: Annotated[
        Optional[list[str]],
        Argument(
            autocompletion=complete_map_slugs,
            help="Map slugs, source ids, or slug globs (e.g. 'ngs-*')",
        ),
    ] = None,
    compilation: Annotated[
        Optional[list[str]],
        Option(
            "--compilation",
            "-c",
            help="Include a compilation and every map beneath it; repeatable",
        ),
    ] = None,
    exclude: MapExclude = None,
    state: MapState = None,
    sources_schema: Annotated[
        bool,
        Option(help="Include the maps' `sources.*` staging tables"),
    ] = True,
    staging_prefix: Annotated[
        Optional[str],
        Option(help="Also search `sources.<prefix>_*`, for maps staged together"),
    ] = None,
    overwrite: bool = Option(False, help="Replace an existing file"),
):
    """Export maps to a GeoPackage that `macrostrat maps ingest` can load.

    Selects single maps, slug globs, or whole compilation trees. Staging tables
    are searched under each map's slug, each compilation's slug and
    `--staging-prefix`; a shared table contributes only the exported maps' rows.
    """
    from macrostrat.core.config import settings

    from ..database import get_database
    from ..utils.map_info import get_map_info, resolve_maps
    from .export import compilation_tree, export_maps

    if output.suffix.lower() != ".gpkg":
        raise MacrostratError(f"{output} must have a .gpkg extension")
    if output.exists() and not overwrite:
        raise MacrostratError(
            f"{output} exists", details="Pass --overwrite to replace it."
        )
    if not maps and not compilation:
        raise MacrostratError("Name at least one map or --compilation")

    db = get_database()
    selectors = list(maps or [])
    prefixes = {staging_prefix} if staging_prefix else set()
    for name in compilation or []:
        root = get_map_info(db, name)
        prefixes.add(root.slug)
        selectors += [str(i) for i in compilation_tree(db, root)]

    selected = resolve_maps(db, selectors, exclude=exclude, state=state)
    console.print(f"Exporting [bold]{len(selected)}[/] maps to [cyan]{output}")
    export_maps(
        db,
        output,
        selected,
        staging=sources_schema,
        staging_prefixes=prefixes,
        metadata=dict(
            exported_from=getattr(settings, "env", None),
            selection=dict(maps=maps or [], compilations=compilation or []),
        ),
    )
    console.print(f"[green]Wrote[/] {output}")


_CHOICES = {
    "o": ("overwrite", False),
    "s": ("skip", False),
    "O": ("overwrite", True),
    "S": ("skip", True),
    "q": ("stop", False),
}


def prompting_resolver():
    """Ask about each conflicting slug, remembering an 'all' answer."""
    from .load import ConflictAction

    if not stdin.isatty():
        return None
    remembered = {}

    def resolve(slug: str):
        if "all" in remembered:
            return remembered["all"]
        answer = Prompt.ask(
            f"Map [item]{slug}[/item] already exists."
            " [bold]o[/]verwrite, [bold]s[/]kip, [bold]O[/]verwrite all,"
            " [bold]S[/]kip all, or [bold]q[/]uit?",
            choices=list(_CHOICES),
            show_choices=False,
            console=console,
        )
        name, for_all = _CHOICES[answer]
        action = ConflictAction(name)
        if for_all:
            remembered["all"] = action
        return action

    return resolve


def ingest_packages(
    packages: list[Path],
    *,
    only: Optional[list[str]] = None,
    on_conflict=None,
    staging: bool = True,
    yes: bool = False,
):
    """The `macrostrat maps ingest` branch for Macrostrat map packages."""
    from macrostrat.core.environment import WriteScope
    from macrostrat.core.safety import require_write_access

    from ..database import get_database
    from .load import ConflictAction, import_package

    on_conflict = ConflictAction(on_conflict or ConflictAction.ask)
    require_write_access(
        WriteScope.Data,
        assume_yes=yes,
        action=f"import of map package {', '.join(p.name for p in packages)}",
    )
    db = get_database()
    resolve = prompting_resolver()
    reports = []
    for path in packages:
        console.print(f"[bold]Importing map package [cyan]{path}")
        report = import_package(
            db,
            path,
            on_conflict=on_conflict,
            resolve=resolve,
            only=only,
            staging=staging,
        )
        reports.append(report)
        console.print(
            f"[green]Imported[/] {len(report.imported)} maps"
            + (
                f" ({len(report.overwritten)} overwritten)"
                if report.overwritten
                else ""
            )
            + (f", skipped {len(report.skipped)}" if report.skipped else "")
            + (f", {len(report.warnings)} warnings" if report.warnings else "")
        )
    if any(r.imported for r in reports):
        console.print(
            "[dim]Legends and topology are rebuilt by processing: run"
            " `macrostrat maps process` on the imported maps, then"
            " `macrostrat topo update`.[/]"
        )
    return reports
