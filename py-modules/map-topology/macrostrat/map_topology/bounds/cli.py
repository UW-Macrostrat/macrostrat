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

from ..manager import filter_maps, get_map_list
from . import build as build_mod
from .operations import CLI_OPERATIONS, BoundaryOp

cli = Typer(no_args_is_help=True, short_help="Compose and edit map boundaries")

add_cli = Typer(
    no_args_is_help=True,
    help="Add a boundary operation. One command per operation type; geometry-"
    "bearing operations are authored in QGIS instead.",
)
cli.add_typer(add_cli, name="add")


def _resolve(maps: list[str]) -> list:
    db = get_database()
    all_maps = get_map_list(db, filter_by=maps)
    if maps:
        all_maps = list(filter_maps(all_maps, maps))
    if not all_maps:
        print("[red]No matching maps[/]")
        raise typer.Exit(1)
    return all_maps


@cli.command("show")
def show(maps: Annotated[list[str], Argument(help="Map slugs or source ids")]):
    """Show a map's boundary operations and composed state."""
    db = get_database()
    for m in _resolve(maps):
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
        Optional[list[str]], Argument(help="Map slugs or source ids")
    ] = None,
    all_maps: Annotated[bool, Option("--all", help="Build every map")] = False,
    init: Annotated[
        bool, Option("--init", help="Recompute the opening union from map features")
    ] = False,
    dry_run: Annotated[
        bool, Option("--dry-run", help="Report the result without writing")
    ] = False,
):
    """Replay a map's operations onto its boundary."""
    if not maps and not all_maps:
        print("[red]Pass one or more maps, or --all[/]")
        raise typer.Exit(1)
    db = get_database()
    targets = get_map_list(db) if all_maps else _resolve(maps)
    failures = 0
    for m in targets:
        res = build_mod.build(db, m.map_id, init=init, dry_run=dry_run)
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
        else:
            verb = "would be" if dry_run else "built"
            area = f"{res.area_km:,.1f} km²" if res.area_km is not None else "?"
            print(f"  [green]{verb}[/] {label} -- {area} from {len(res.ops)} ops")
    if failures:
        raise typer.Exit(1)


@cli.command("rm")
def remove(
    map: Annotated[str, Argument(help="Map slug or source id")],
    op_id: Annotated[int, Argument(help="Operation id, from `bounds show`")],
):
    """Remove a boundary operation."""
    db = get_database()
    m = _resolve([map])[0]
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
    m = _resolve([map])[0]
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
                "UPDATE map_bounds.boundary_op SET position = :position"
                " WHERE id = :id",
                dict(id=o.id, position=index),
            )
    db.session.commit()
    print(f"Moved operation {op_id} to position {ops.index(target) + 1}")
    print("[dim]Run `macrostrat bounds build` to apply.[/]")


@cli.command("reset")
def reset(map: Annotated[str, Argument(help="Map slug or source id")]):
    """Drop every boundary operation for a map."""
    db = get_database()
    m = _resolve([map])[0]
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


def _append(map: str, operation: str, model: BoundaryOp) -> None:
    db = get_database()
    m = _resolve([map])[0]
    opening = build_mod.ensure_opening(db, m.map_id)
    if opening is None:
        print(
            f"[red]{m.slug} has no boundary geometry to build on.[/] "
            "Run `macrostrat bounds build --init` first."
        )
        raise typer.Exit(1)
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
    db.session.commit()
    print(f"Added [bold]{operation}[/] at position {position} on {m.slug}")
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
            "map",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Annotated[str, Argument(help="Map slug or source id")],
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
        map_ = kwargs.pop("map")
        supplied = {k: v for k, v in kwargs.items() if v is not None}
        try:
            model = model_cls(**supplied)
        except Exception as err:  # noqa: BLE001 -- surfaced as a CLI message
            print(f"[red]{err}[/]")
            raise typer.Exit(1)
        _append(map_, op_id, model)

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
