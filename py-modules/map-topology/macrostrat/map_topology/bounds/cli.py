"""`macrostrat bounds` -- compose map boundaries from ordered operations.

Geometry-bearing operations (`add`, `subtract`, `init`, `adopt`) are authored in
QGIS, which edits `map_bounds.boundary_op` directly as a PostGIS layer. This CLI
covers the parameter-only operations, ordering, inspection and building.
"""

import inspect
from typing import Annotated, Optional, get_args, get_origin

import typer
from rich import print
from rich.table import Table
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database
from macrostrat.map_integration.utils.map_info import (
    MapExclude,
    MapSelector,
    MapState,
    resolve_maps,
)

from . import build as build_mod
from .operations import CLI_OPERATIONS, OPENING_OPERATIONS, BoundaryOp

cli = Typer(no_args_is_help=True, short_help="Compose and edit map boundaries")

add_cli = Typer(
    no_args_is_help=True,
    help="Add a boundary operation. One command per operation type; geometry-"
    "bearing operations are authored in QGIS instead.",
)
cli.add_typer(add_cli, name="add")


def _sources_with_bounds(db):
    """Every source with a `map_area` row -- maps and compilations alike."""
    return db.run_query(
        """
        SELECT a.source_id AS map_id, s.slug, s.scale, a.area_km
        FROM map_bounds.map_area a
        JOIN maps.sources s ON s.source_id = a.source_id
        ORDER BY a.area_km DESC NULLS LAST
        """
    ).all()


def _resolve(
    maps: list[str], exclude: list[str] | None = None, state: str | None = None
) -> list:
    """Resolve selectors as `macrostrat maps` does, keeping maps that have bounds."""
    db = get_database()
    selected = resolve_maps(db, maps, exclude=exclude, state=state)
    with_bounds = {m.map_id: m for m in _sources_with_bounds(db)}
    missing = [m.slug for m in selected if m.id not in with_bounds]
    if missing:
        print(
            f"[yellow]Skipping {len(missing)} maps with no bounds:[/] {', '.join(missing)}"
        )
    result = [with_bounds[m.id] for m in selected if m.id in with_bounds]
    if not result:
        print("[red]No matching maps have bounds[/]")
        raise typer.Exit(1)
    return result


def _resolve_one(map: str):
    result = _resolve([map])
    if len(result) > 1:
        print(f"[red]{map!r} matches {len(result)} maps; this command takes one[/]")
        raise typer.Exit(1)
    return result[0]


@cli.command("show")
def show(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Show a map's boundary operations and composed state."""
    db = get_database()
    for m in _resolve(maps, exclude, state):
        ops = build_mod.load_ops(db, m.map_id)
        row = db.run_query(
            "SELECT area_km, boundary_error, geometry IS NULL AS empty"
            " FROM map_bounds.map_area WHERE source_id = :source_id",
            dict(source_id=m.map_id),
        ).first()
        header = f"[bold green]{m.slug}[/] [dim]#{m.map_id}[/]"
        if row is not None and row.area_km is not None:
            header += f"  [green]{row.area_km:,.1f}[/] km²"
        print(header)
        if row is not None and row.boundary_error:
            print(f"  [red]boundary error:[/] {row.boundary_error}")
        if not ops:
            print("  [dim]no operations -- boundary is the plain feature union[/]")
            continue
        table = Table(box=None, pad_edge=False, show_edge=False)
        for col in ("pos", "id", "operation", "parameters", "note"):
            table.add_column(col, overflow="fold")
        for o in ops:
            params = o.op.model_dump(exclude_defaults=True, mode="json")
            marker = " [dim](geometry)[/]" if o.has_geometry else ""
            table.add_row(
                str(o.position),
                str(o.id),
                o.operation + marker,
                ", ".join(f"{k}={v}" for k, v in params.items()) or "[dim]--[/]",
                o.note or "",
            )
        print(table)


@cli.command("build")
def build_cmd(
    maps: Annotated[
        Optional[list[str]],
        Argument(help="Map slugs, source ids, or slug globs (e.g. 'ngs-*')"),
    ] = None,
    exclude: MapExclude = None,
    state: MapState = None,
    all_maps: Annotated[
        bool,
        Option(
            "--all",
            help="Build every map whose operations changed since its last build",
        ),
    ] = False,
    rebuild: Annotated[
        bool, Option("--rebuild", help="With --all, build unchanged maps too")
    ] = False,
    strict: Annotated[
        bool,
        Option(
            "--strict",
            help=f"Write any change, not only those over {build_mod.TOLERANCE_KM:g} km²"
            f" or {build_mod.TOLERANCE_REL:g} of the map's area",
        ),
    ] = False,
    init: Annotated[
        bool, Option("--init", help="Recompute the opening union from map features")
    ] = False,
    dry_run: Annotated[
        bool, Option("--dry-run", help="Report the result without writing")
    ] = False,
):
    """Replay a map's operations onto its boundary.

    Named maps are always rebuilt. A rebuilt boundary within tolerance of the
    stored one is left in place, so it is not re-noded.
    """
    if not maps and not all_maps:
        print("[red]Pass one or more maps, or --all[/]")
        raise typer.Exit(1)
    if all_maps and (maps or exclude or state):
        print("[red]--all takes no map selectors, --exclude or --state[/]")
        raise typer.Exit(1)
    db = get_database()
    if not all_maps:
        targets = _resolve(maps, exclude, state)
    elif rebuild:
        targets = _sources_with_bounds(db)
    else:
        stale = build_mod.needs_build(db)
        everything = _sources_with_bounds(db)
        targets = [m for m in everything if m.map_id in stale]
        print(
            f"[dim]{len(everything) - len(targets)} maps up to date;"
            " --rebuild to build them anyway[/]"
        )

    failures = 0
    for m in targets:
        res = build_mod.build(db, m.map_id, init=init, dry_run=dry_run, strict=strict)
        label = f"[bold]{res.slug or m.map_id}[/]"
        if res.error:
            failures += 1
            where = (
                f" at position {res.failed_op.position} ({res.failed_op.operation})"
                if res.failed_op
                else ""
            )
            print(f"  [red]FAILED[/] {label}{where}: {res.error}")
        elif res.skipped:
            print(f"  [dim]skipped[/] {label} -- {res.skipped}")
        elif res.unchanged:
            if res.diff_km:
                print(
                    f"  [dim]unchanged[/] {label} -- moved {res.diff_km:,.4g} km²,"
                    " within tolerance; --strict to write"
                )
            else:
                print(f"  [dim]unchanged[/] {label}")
        else:
            verb = "would be" if dry_run else "built"
            area = f"{res.area_km:,.1f} km²" if res.area_km is not None else "?"
            print(f"  [green]{verb}[/] {label} -- {area} from {len(res.ops)} ops")
    if failures:
        raise typer.Exit(1)


@cli.command("open")
def open_cmd(
    map: Annotated[str, Argument(help="Map or compilation slug or source id")],
    operation: Annotated[
        str, Argument(help="Opening operation: union, compile, world, adopt, init")
    ],
):
    """Set how a boundary opens, replacing the existing opening operation.

    `compile` unions the bounds of every noded source below a compilation;
    `world` asserts the whole world. The cached geometry is cleared and
    recomputed by the next `bounds build` or `topo update`.
    """
    if operation not in OPENING_OPERATIONS:
        print(f"[red]{operation} cannot open a boundary[/]")
        raise typer.Exit(1)
    db = get_database()
    m = _resolve_one(map)
    build_mod.set_opening(db, m.map_id, operation)
    db.session.commit()
    print(f"{m.slug} now opens with [bold]{operation}[/]")
    print("[dim]Run `macrostrat bounds build` to apply.[/]")


@cli.command("rm")
def remove(
    map: Annotated[str, Argument(help="Map slug or source id")],
    op_id: Annotated[int, Argument(help="Operation id, from `bounds show`")],
):
    """Remove a boundary operation."""
    db = get_database()
    m = _resolve_one(map)
    deleted = db.run_query(
        "DELETE FROM map_bounds.boundary_op"
        " WHERE id = :id AND source_id = :source_id RETURNING position, operation",
        dict(id=op_id, source_id=m.map_id),
    ).first()
    if deleted is None:
        print(f"[red]No operation {op_id} on {m.slug}[/]")
        raise typer.Exit(1)
    db.session.commit()
    print(f"Removed {deleted.operation} at position {deleted.position}")
    print("[dim]Run `macrostrat bounds build` to apply.[/]")


@cli.command("move")
def move(
    map: Annotated[str, Argument(help="Map slug or source id")],
    op_id: Annotated[int, Argument(help="Operation id, from `bounds show`")],
    position: Annotated[int, Argument(help="New position (1 or greater)")],
):
    """Reorder a boundary operation."""
    if position < 1:
        print("[red]Position 0 is reserved for the opening operation[/]")
        raise typer.Exit(1)
    db = get_database()
    m = _resolve_one(map)
    ops = [o for o in build_mod.load_ops(db, m.map_id) if o.position > 0]
    target = next((o for o in ops if o.id == op_id), None)
    if target is None:
        print(f"[red]No movable operation {op_id} on {m.slug}[/]")
        raise typer.Exit(1)

    ops.remove(target)
    ops.insert(min(position, len(ops) + 1) - 1, target)

    # Renumber the whole list rather than swapping pairs: the unique constraint
    # is only satisfied again once every row has moved, so defer it for the
    # transaction and write a clean 1..N sequence.
    db.run_query("SET CONSTRAINTS map_bounds.boundary_op_unique_position DEFERRED")
    for index, o in enumerate(ops, start=1):
        if o.position != index:
            db.run_query(
                "UPDATE map_bounds.boundary_op SET position = :position WHERE id = :id",
                dict(id=o.id, position=index),
            )
    db.session.commit()
    print(f"Moved operation {op_id} to position {ops.index(target) + 1}")
    print("[dim]Run `macrostrat bounds build` to apply.[/]")


@cli.command("reset")
def reset(map: Annotated[str, Argument(help="Map slug or source id")]):
    """Drop every boundary operation for a map."""
    db = get_database()
    m = _resolve_one(map)
    n = db.run_query(
        "SELECT count(*) FROM map_bounds.boundary_op WHERE source_id = :source_id",
        dict(source_id=m.map_id),
    ).scalar()
    if not n:
        print(f"[dim]{m.slug} has no operations[/]")
        return
    answer = input(f"Remove {n} operations from {m.slug}? [y/N] ")
    if answer.lower() not in ("y", "yes"):
        return
    db.run_query(
        "DELETE FROM map_bounds.boundary_op WHERE source_id = :source_id",
        dict(source_id=m.map_id),
    )
    db.session.commit()
    print(f"Removed {n} operations")


def _append(
    maps: list[str],
    exclude: list[str] | None,
    state: str | None,
    operation: str,
    model: BoundaryOp,
) -> None:
    db = get_database()
    targets = _resolve(maps, exclude, state)
    no_geometry = []
    for m in targets:
        if build_mod.ensure_opening(db, m.map_id) is None:
            no_geometry.append(m.slug)
            continue
        position = db.run_query(
            "SELECT coalesce(max(position), 0) + 1 FROM map_bounds.boundary_op"
            " WHERE source_id = :source_id",
            dict(source_id=m.map_id),
        ).scalar()
        db.run_query(
            """
            INSERT INTO map_bounds.boundary_op
              (source_id, position, operation, parameters)
            VALUES (:source_id, :position, :operation, :parameters::jsonb)
            """,
            dict(
                source_id=m.map_id,
                position=position,
                operation=operation,
                parameters=model.model_dump_json(),
            ),
        )
        print(f"Added [bold]{operation}[/] at position {position} on {m.slug}")
    # One commit, so a selection is never left half-edited.
    if no_geometry:
        db.session.rollback()
        print(
            f"[red]{len(no_geometry)} maps have no boundary geometry to build on:[/] "
            f"{', '.join(no_geometry)}. Run `macrostrat bounds build --init` on them,"
            " or --exclude them. Nothing was added."
        )
        raise typer.Exit(1)
    db.session.commit()
    print("[dim]Run `macrostrat bounds build` to apply.[/]")


def _register_add_commands() -> None:
    """Generate one `bounds add` command per parameter-only operation.

    The Pydantic model is the single definition: its fields become CLI options,
    its docstring becomes the help text, and its validation is what the CLI
    enforces -- so an operation cannot drift from its command.
    """
    for op_id, model_cls in CLI_OPERATIONS.items():
        _register_one(op_id, model_cls)


def _register_one(op_id: str, model_cls: type[BoundaryOp]) -> None:
    fields = model_cls.model_fields
    params = [
        inspect.Parameter(
            "maps", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=MapSelector
        )
    ]
    for name, info in fields.items():
        required = info.is_required()
        annotation = info.annotation
        # Unit-bearing types are parsed from strings like "0.5km".
        cli_type = str if _is_quantity(annotation) else annotation
        if required:
            params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=Annotated[
                        cli_type, Argument(help=info.description or name)
                    ],
                )
            )
        else:
            params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=Annotated[
                        Optional[cli_type], Option(help=info.description or name)
                    ],
                )
            )

    def command(**kwargs):
        maps = kwargs.pop("maps")
        exclude = kwargs.pop("exclude")
        state = kwargs.pop("state")
        supplied = {k: v for k, v in kwargs.items() if v is not None}
        try:
            model = model_cls(**supplied)
        except Exception as err:  # noqa: BLE001 -- surfaced as a CLI message
            print(f"[red]{err}[/]")
            raise typer.Exit(1)
        _append(maps, exclude, state, op_id, model)

    for name, annotation in (("exclude", MapExclude), ("state", MapState)):
        params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
                annotation=annotation,
            )
        )

    command.__signature__ = inspect.Signature(params)
    command.__name__ = op_id
    command.__doc__ = (model_cls.__doc__ or "").strip()
    add_cli.command(op_id.replace("_", "-"))(command)


def _is_quantity(annotation) -> bool:
    from .units import Area, Distance

    if annotation in (Distance, Area):
        return True
    return any(a in (Distance, Area) for a in get_args(annotation))


_register_add_commands()
