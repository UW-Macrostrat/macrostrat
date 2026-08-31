"""`macrostrat compilations` -- assemble maps out of other maps.

A compilation is a map: a `maps.sources` row with members. There is no kind
flag -- "is a compilation" means *has members*, and "is a constituent" means
*is a member* -- so every command here reads and writes `map_bounds.compilation_member`
and derives the rest.
"""

from typing import Annotated, Optional

import typer
from rich import print
from rich.table import Table
from typer import Argument, Option, Typer

from macrostrat.core.database import get_database

from .manager import proc

cli = Typer(no_args_is_help=True, short_help="Assemble maps out of other maps")


def _resolve(name: str) -> tuple[int, str]:
    """Resolve a slug or source id. Reads `maps.sources`, not `map_area`: a
    compilation has no boundary until its members give it one."""
    db = get_database()
    row = db.run_query(
        """
        SELECT source_id, slug FROM maps.sources
        WHERE slug = :name OR source_id::text = :name
        """,
        dict(name=name),
    ).first()
    if row is None:
        print(f"[red]No map matching[/] {name}")
        raise typer.Exit(1)
    return row.source_id, row.slug


@cli.command("list")
def list_compilations():
    """List compilations and whether their polygons are current."""
    db = get_database()
    rows = db.run_query(
        """
        SELECT source_id, slug, n_members, assembly_mode, state
        FROM map_bounds.compilation_sync
        ORDER BY slug
        """
    ).all()
    if not rows:
        print("[dim]No compilations[/]")
        return
    table = Table()
    for col in ("Compilation", "Members", "Mode", "State"):
        table.add_column(col)
    colors = {"virtual": "dim", "current": "green", "stale": "yellow"}
    for r in rows:
        table.add_row(
            f"{r.slug} [dim]#{r.source_id}[/]",
            str(r.n_members),
            r.assembly_mode,
            f"[{colors.get(r.state, 'white')}]{r.state}[/]",
        )
    print(table)


@cli.command("create")
def create(
    slug: Annotated[str, Argument(help="Slug for the new compilation")],
    members: Annotated[list[str], Argument(help="Member slugs or source ids, lowest priority first")],
    name: Annotated[Optional[str], Option(help="Display name")] = None,
    scale: Annotated[Optional[str], Option(help="Scale band; defaults to the members'")] = None,
    priority: Annotated[Optional[int], Option(help="Priority within its layer")] = None,
):
    """Create a compilation from existing maps.

    Members are given lowest-priority first, so the last one wins where they
    overlap -- `create bc-surface bc_2017 bc_2017_quat` puts surficial on top.
    The compilation is virtual: it holds no polygons, and resolution descends
    through it to whichever member has the geometry.
    """
    db = get_database()
    resolved = [_resolve(m) for m in members]

    scales = {
        db.run_query(
            "SELECT scale FROM maps.sources WHERE source_id = :id", dict(id=sid)
        ).scalar()
        for sid, _ in resolved
    }
    if scale is None:
        if len(scales) != 1 or None in scales:
            print(f"[red]Members disagree on scale ({scales}); pass --scale[/]")
            raise typer.Exit(1)
        scale = scales.pop()

    if priority is None:
        # Take the standing of the member that currently wins, so the compilation
        # occupies the position its top layer already had.
        priority = db.run_query(
            "SELECT max(coalesce(new_priority, 0)) FROM maps.sources"
            " WHERE source_id = ANY(:ids)",
            dict(ids=[sid for sid, _ in resolved]),
        ).scalar()

    source_id = db.run_query(
        """
        INSERT INTO maps.sources (slug, name, scale, new_priority, status_code, is_finalized)
        VALUES (:slug, :name, :scale, :priority, 'active', false)
        ON CONFLICT (slug) DO NOTHING
        RETURNING source_id
        """,
        dict(slug=slug, name=name or slug, scale=scale, priority=priority),
    ).scalar()
    if source_id is None:
        print(f"[red]A source with slug[/] {slug} [red]already exists[/]")
        raise typer.Exit(1)

    for offset, (member_id, member_slug) in enumerate(resolved, start=1):
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority)
            VALUES (:compilation_id, :member_id, :priority)
            """,
            dict(compilation_id=source_id, member_id=member_id, priority=offset),
        )
        print(f"[green]+[/] {slug} <- {member_slug} [dim](priority {offset})[/]")
    db.session.commit()
    print(
        f"[green]{slug}[/] [dim]#{source_id}[/] created as {scale}, priority {priority}."
        "\nRun [cyan]macrostrat compilations sync[/] to derive its boundary and paths."
    )


@cli.command("show")
def show(compilation: Annotated[str, Argument(help="Slug or source id")]):
    """Show a compilation's members, highest priority first."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    rows = db.run_query(
        """
        SELECT
          mc.member_id, s.slug, mc.priority, mc.role,
          map_bounds.holds_polygons(mc.member_id) AS holds_polygons
        FROM map_bounds.compilation_member mc
        JOIN maps.sources s ON s.source_id = mc.member_id
        WHERE mc.compilation_id = :source_id
        ORDER BY mc.priority DESC NULLS LAST, s.slug
        """,
        dict(source_id=source_id),
    ).all()
    print(f"[bold green]{slug}[/] [dim]#{source_id}[/]")
    if not rows:
        print("  [dim]no members[/]")
        return
    for r in rows:
        priority = "[dim]--[/]" if r.priority is None else str(r.priority)
        # A member without polygons is descended through when identity is
        # resolved; one with polygons is where resolution stops.
        leaf = "" if r.holds_polygons else " [dim](virtual)[/]"
        role = f" [cyan]{r.role}[/]" if r.role else ""
        print(f"  {priority:>4}  {r.slug} [dim]#{r.member_id}[/]{role}{leaf}")


@cli.command("add")
def add(
    compilation: Annotated[str, Argument(help="Slug or source id")],
    members: Annotated[list[str], Argument(help="Member slugs or source ids")],
    priority: Annotated[
        Optional[int],
        Option(help="Priority of the first member; later members ascend from it"),
    ] = None,
    role: Annotated[Optional[str], Option(help="Membership role")] = None,
):
    """Add members to a compilation."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    for offset, member in enumerate(members):
        member_id, member_slug = _resolve(member)
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority, role)
            VALUES (:compilation_id, :member_id, :priority, :role)
            ON CONFLICT (compilation_id, member_id) DO UPDATE
              SET priority = EXCLUDED.priority, role = EXCLUDED.role
            """,
            dict(
                compilation_id=source_id,
                member_id=member_id,
                priority=None if priority is None else priority + offset,
                role=role,
            ),
        )
        print(f"[green]+[/] {slug} <- {member_slug}")
    db.session.commit()


@cli.command("rm")
def remove(
    compilation: Annotated[str, Argument(help="Slug or source id")],
    members: Annotated[list[str], Argument(help="Member slugs or source ids")],
):
    """Remove members from a compilation."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    for member in members:
        member_id, member_slug = _resolve(member)
        db.run_query(
            """
            DELETE FROM map_bounds.compilation_member
            WHERE compilation_id = :compilation_id AND member_id = :member_id
            """,
            dict(compilation_id=source_id, member_id=member_id),
        )
        print(f"[red]-[/] {slug} <- {member_slug}")
    db.session.commit()


@cli.command("mode")
def mode(
    compilation: Annotated[str, Argument(help="Slug or source id")],
    assembly_mode: Annotated[str, Argument(help="disjoint | layered")],
):
    """Set how a compilation's members fit together.

    `layered` means they overlap and priority resolves them; `disjoint` means
    they mosaic cleanly. Not derivable -- it is an assertion about the data.
    """
    if assembly_mode not in ("disjoint", "layered"):
        print("[red]Mode must be 'disjoint' or 'layered'[/]")
        raise typer.Exit(1)
    db = get_database()
    source_id, slug = _resolve(compilation)
    db.run_query(
        """
        INSERT INTO map_bounds.compilation (source_id, assembly_mode)
        VALUES (:source_id, :assembly_mode)
        ON CONFLICT (source_id) DO UPDATE SET assembly_mode = EXCLUDED.assembly_mode
        """,
        dict(source_id=source_id, assembly_mode=assembly_mode),
    )
    db.session.commit()
    print(f"[green]{slug}[/] is {assembly_mode}")


@cli.command("materialize")
def materialize(
    compilation: Annotated[str, Argument(help="Slug or source id")],
    apply: Annotated[bool, Option("--apply/--dry-run", help="Write the polygons")] = False,
):
    """Give a compilation polygons of its own, clipped from its members'.

    Turns a virtual compilation into one that holds the assembled surface
    directly, so resolution stops at it instead of descending. Members keep
    their own polygons, so this is reversible with `dematerialize`.
    """
    db = get_database()
    source_id, slug = _resolve(compilation)

    estimate = db.run_query(
        """
        SELECT count(*) AS faces,
               sum((SELECT count(*) FROM maps.polygons p
                    WHERE p.source_id = cm.member_id
                      AND ST_Intersects(p.geom, f.geometry))) AS polygon_clips
        FROM map_bounds.compilation_member cm
        JOIN map_bounds_topology.map_face f
          ON f.map_id = cm.member_id
         AND f.map_layer = map_bounds.face_layer_for(:source_id)
        WHERE cm.compilation_id = :source_id
        """,
        dict(source_id=source_id),
    ).first()

    if not estimate or not estimate.faces:
        print(f"[red]{slug}[/] has no member faces to clip; run [cyan]sync[/] first")
        raise typer.Exit(1)

    print(
        f"[bold]{slug}[/] [dim]#{source_id}[/]: "
        f"{estimate.faces} faces, ~{estimate.polygon_clips} polygon clips"
    )
    if not apply:
        print("[dim]Dry run. Pass --apply to write.[/]")
        return

    db.run_sql(proc("materialize-compilation"), dict(compilation_id=source_id))
    db.session.commit()
    n = db.run_query(
        "SELECT count(*) FROM maps.polygons WHERE source_id = :id",
        dict(id=source_id),
    ).scalar()
    print(
        f"[green]{n}[/] polygons written."
        "\nRun [cyan]macrostrat compilations sync[/], then reprocess the topology"
        " so faces resolve to it rather than its members."
    )


@cli.command("dematerialize")
def dematerialize(
    compilation: Annotated[str, Argument(help="Slug or source id")],
):
    """Drop a compilation's derived polygons, returning it to virtual."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    n = db.run_query(
        "SELECT count(*) FROM maps.polygons WHERE source_id = :id", dict(id=source_id)
    ).scalar()
    db.run_sql(proc("dematerialize-compilation"), dict(compilation_id=source_id))
    db.session.commit()
    print(f"[green]{slug}[/]: {n} derived polygons removed; now virtual.")


@cli.command("sync")
def sync():
    """Rebuild everything derived from compilation membership.

    The same three steps `macrostrat topo update` runs, without the per-map
    topology work in between -- for picking up a membership edit, or for
    finishing a schema apply. Order matters: `sync-priority-paths` empties
    `map_priority` and rebuilds it from the membership edges, so the placements
    have to be written first.
    """
    db = get_database()
    # Order matters, and not only for the reason above: `set-map-priority` places
    # a map in its layer only if it has a boundary, and a new compilation gets one
    # from `sync-compilation-bounds`. Run the other way round and a compilation is
    # never placed on its first sync -- while its members have already been retired
    # from the layer, so they vanish from resolution entirely.
    for step in (
        "sync-compilation-bounds",
        "set-map-priority",
        "sync-priority-paths",
        "sync-unit-faces",
    ):
        db.run_sql(proc(step))
    db.session.commit()
    counts = db.run_query(
        """
        SELECT count(*) AS resolved, count(DISTINCT map_layer) AS layers
        FROM map_bounds.map_priority
        """
    ).first()
    print(
        f"[green]{counts.resolved}[/] resolutions across "
        f"[green]{counts.layers}[/] served layers"
    )
