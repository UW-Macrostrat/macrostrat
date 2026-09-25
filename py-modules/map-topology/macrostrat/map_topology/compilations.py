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

from . import carto_v1
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


def _is_ingested(db, source_id: int) -> bool:
    """Whether the compilation holds polygons that are originals, not a cache."""
    return bool(
        db.run_query(
            "SELECT map_bounds.is_materialized(:id) AND NOT map_bounds.is_derived(:id)",
            dict(id=source_id),
        ).scalar()
    )


def _refuse_if_ingested(db, source_id: int, slug: str, verb: str):
    """Guard the polygon-rewriting commands.

    Only a cache can be dematerialized -- it came from the members and can go
    back to them -- and only a virtual compilation can be materialized. Ingested
    polygons are the original dataset, and `dematerialize` would delete them
    outright. (The procedure re-checks this polygon by polygon.)
    """
    if not _is_ingested(db, source_id):
        return
    print(
        f"[red]{slug}[/] holds ingested content: its members are provenance, not"
        f" material, so there is nothing to {verb}."
        "\n[dim]Its polygons are the original dataset, not a derived cache.[/]"
    )
    raise typer.Exit(1)


#: What makes a member a poor candidate for a compilation.
#:
#: These used to be enforced by the layer sweep, which silently withdrew a
#: superseded or non-surface map from every served layer on the next sync. That
#: was the wrong moment and the wrong verb: it destroyed authored edges behind
#: the operator, and a map going out of date is news, not a reason to rewrite
#: somebody's curation. They are checked here instead -- when membership is
#: authored -- so a dumb compilation is not created in the first place, and
#: `lint` reports the ones that went stale afterwards without touching them.
#:
#: The geolayer test applies only where the compilation is a served layer, which
#: is what the retired rule actually meant: a scale layer is a *surface* layer,
#: so a Quaternary or basement map has no place directly in one. Inside an
#: authored compilation the opposite is true -- drawing on several geolayers is
#: the whole job. `ngs-surface` is built out of Quaternary sheets and
#: `ngs-bedrock` out of pre-Quaternary ones, and neither is a mistake; what would
#: be a mistake is placing either of *them* in `medium` while declaring something
#: other than surface.
_MEMBER_CHECK = """
SELECT
  s.slug,
  sup.slug AS superseded_by,
  coalesce(s.geolayer, 'surface') AS member_geolayer,
  coalesce(c.geolayer, 'surface') AS compilation_geolayer,
  map_bounds.has_faces(c.source_id) AS compilation_is_layer,
  EXISTS (
    SELECT 1 FROM map_bounds.compilation_member cm
    WHERE cm.compilation_id = s.source_id
  ) AS has_members
FROM maps.sources s
LEFT JOIN maps.sources sup ON sup.source_id = s.superseded_by
CROSS JOIN maps.sources c
WHERE c.source_id = :compilation_id
  AND s.source_id = ANY(:member_ids)
ORDER BY s.slug
"""


def _refuse_if_materialized(db, source_id: int, slug: str):
    """`materialize` appends: it never deletes the polygons a previous run wrote.

    So a compilation already holding derived polygons must be dematerialized
    first, or a second copy of every polygon lands under its `source_id`.
    """
    derived = db.run_query(
        "SELECT map_bounds.is_derived(:id), map_bounds.is_stale(:id)",
        dict(id=source_id),
    ).first()
    if not derived[0]:
        return
    state = "stale" if derived[1] else "current"
    print(
        f"[red]{slug}[/] already holds derived polygons ({state})."
        f"\n[dim]Run [cyan]macrostrat compilations dematerialize {slug}[/] first,"
        " then materialize again.[/]"
    )
    raise typer.Exit(1)


def _member_problems(db, compilation_id: int, member_ids: list[int]):
    """Reasons each member is a questionable fit, as (slug, reason) pairs."""
    problems = []
    for r in db.run_query(
        _MEMBER_CHECK, dict(compilation_id=compilation_id, member_ids=member_ids)
    ):
        if r.superseded_by is not None:
            problems.append((r.slug, f"superseded by {r.superseded_by}"))
        if r.compilation_is_layer and r.member_geolayer != r.compilation_geolayer:
            problems.append(
                (
                    r.slug,
                    f"depicts {r.member_geolayer}, the layer depicts"
                    f" {r.compilation_geolayer}",
                )
            )
    return problems


def _check_members(
    db, compilation_id: int, slug: str, member_ids: list[int], force: bool
):
    """Refuse the edit if any member is a poor fit, unless overridden.

    Refusing rather than warning is the point: the whole reason layer membership
    stopped being swept is that curation should be deliberate, and a check that
    only prints is one nobody reads in a pipeline.
    """
    problems = _member_problems(db, compilation_id, member_ids)
    if not problems:
        return
    for member, reason in problems:
        mark = "[yellow]![/]" if force else "[red]x[/]"
        print(f"  {mark} {member}: {reason}")
    if force:
        print(f"[yellow]Adding to[/] {slug} [yellow]anyway[/] [dim](--force)[/]")
        return
    print(
        f"[red]Refusing to write[/] {slug}."
        "\n[dim]Pass --force if the membership is intended despite this.[/]"
    )
    raise typer.Exit(1)


def _reparent(db, compilation_id: int, member_ids: list[int]) -> list[tuple[str, str]]:
    """Withdraw members' own edges in layers they now reach through `compilation_id`.

    A map that belongs to a compilation is placed *through* it, not beside it:
    its standing in the layer descends from the compilation's. Leaving both edges
    in place puts the same map in the layer twice, once at `{p}` and once at
    `{p_compilation, p}`, which resolves to the same answer by a longer route and
    makes the shorter one look like a deliberate second opinion.

    The sweep did this implicitly on every run. Doing it here, once, at the
    moment the membership is authored, is the same act made visible -- and
    reversible, since nothing will re-apply it.
    """
    rows = db.run_query(
        """
        DELETE FROM map_bounds.compilation_member direct
        USING map_bounds.compilation_member parent,
              maps.sources layer, maps.sources member
        WHERE direct.member_id = ANY(:member_ids)
          AND parent.compilation_id = direct.compilation_id
          AND parent.member_id = :compilation_id
          AND layer.source_id = direct.compilation_id
          AND member.source_id = direct.member_id
        RETURNING layer.slug AS layer_slug, member.slug AS member_slug
        """,
        dict(compilation_id=compilation_id, member_ids=member_ids),
    ).all()
    return [(r.layer_slug, r.member_slug) for r in rows]


@cli.command("list")
def list_compilations():
    """List compilations and whether their polygons are current."""
    db = get_database()
    # `Members` is what the compilation is authored from; `Sources` is what it
    # actually resolves to, descending through member compilations to the maps at
    # the bottom -- so `carto-large` reads 2 and 284.
    rows = db.run_query(
        """
        SELECT cs.source_id, cs.slug, cs.n_members, cs.assembly_mode,
            cs.is_materialized, cs.is_derived, cs.is_stale,
            l.n_sources
        FROM map_bounds.compilation_sync cs
        CROSS JOIN LATERAL (
            SELECT count(*) AS n_sources
            FROM map_bounds.members_of(cs.source_id, true) m
            WHERE NOT map_bounds.is_compilation(m.source_id)
        ) l
        ORDER BY cs.slug
        """
    ).all()
    if not rows:
        print("[dim]No compilations[/]")
        return
    table = Table()
    for col in ("Compilation", "Members", "Sources", "Mode", "Content"):
        table.add_column(col)
    for r in rows:
        # Three facts, no names for their combinations: holds polygons; those
        # polygons are a cache of the members'; the cache is out of date.
        if not r.is_materialized:
            content = "[dim]virtual[/]"
        elif not r.is_derived:
            content = "[cyan]materialized[/]"
        elif r.is_stale:
            content = "[yellow]materialized, derived, stale[/]"
        else:
            content = "[green]materialized, derived[/]"
        if r.n_sources == r.n_members:
            # Nothing below the members is itself a compilation.
            n_sources = f"[dim]{r.n_sources}[/]"
        else:
            n_sources = str(r.n_sources)
        table.add_row(
            f"{r.slug} [dim]#{r.source_id}[/]",
            str(r.n_members),
            n_sources,
            r.assembly_mode,
            content,
        )
    print(table)


@cli.command("create")
def create(
    slug: Annotated[str, Argument(help="Slug for the new compilation")],
    members: Annotated[
        list[str], Argument(help="Member slugs or source ids, lowest priority first")
    ],
    name: Annotated[Optional[str], Option(help="Display name")] = None,
    scale: Annotated[
        Optional[str], Option(help="Scale band; defaults to the members'")
    ] = None,
    priority: Annotated[Optional[int], Option(help="Priority within its layer")] = None,
    layer: Annotated[
        Optional[str], Option(help="Layer to place the compilation in, e.g. `medium`")
    ] = None,
    force: Annotated[
        bool, Option(help="Author the membership despite failed checks")
    ] = False,
):
    """Create a compilation from existing maps.

    Members are given lowest-priority first, so the last one wins where they
    overlap -- `create bc-surface bc_2017 bc_2017_quat` puts surficial on top.
    The compilation is virtual: it holds no polygons, and resolution descends
    through it to whichever member has the geometry.

    Pass `--layer` to place it somewhere it will actually be resolved. Layer
    membership is authored like any other, so a compilation created without one
    exists, can be inspected, and is served nowhere -- which is a reasonable
    thing to want (`carto-v1` is exactly that) but is rarely what you meant.
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

    _check_members(db, source_id, slug, [sid for sid, _ in resolved], force)

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

    if layer is not None:
        layer_id, layer_slug = _resolve(layer)
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority)
            VALUES (:layer_id, :compilation_id, :priority)
            ON CONFLICT (compilation_id, member_id)
            DO UPDATE SET priority = EXCLUDED.priority
            """,
            dict(layer_id=layer_id, compilation_id=source_id, priority=priority),
        )
        print(f"[green]+[/] {layer_slug} <- {slug} [dim](priority {priority})[/]")
        for lyr, member in _reparent(db, source_id, [sid for sid, _ in resolved]):
            print(f"[red]-[/] {lyr} <- {member} [dim](now placed through {slug})[/]")

    db.session.commit()
    placed = f"in {layer}, priority {priority}" if layer else "[yellow]unplaced[/]"
    print(
        f"[green]{slug}[/] [dim]#{source_id}[/] created as {scale}, {placed}."
        "\nRun [cyan]macrostrat topo update[/] to derive its boundary and solve its faces."
    )


@cli.command("show")
def show(compilation: Annotated[str, Argument(help="Slug or source id")]):
    """Show a compilation's members, highest priority first."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    rows = db.run_query(
        """
        SELECT
          mc.member_id, s.slug, mc.priority,
          map_bounds.is_materialized(mc.member_id) AS is_materialized
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
        virtual = "" if r.is_materialized else " [dim](virtual)[/]"
        print(f"  {priority:>4}  {r.slug} [dim]#{r.member_id}[/]{virtual}")


@cli.command("add")
def add(
    compilation: Annotated[str, Argument(help="Slug or source id")],
    members: Annotated[list[str], Argument(help="Member slugs or source ids")],
    priority: Annotated[
        Optional[int],
        Option(help="Priority of the first member; later members ascend from it"),
    ] = None,
    reparent: Annotated[
        bool,
        Option(
            help="Withdraw members' own edges in layers they now reach through this"
        ),
    ] = True,
    force: Annotated[
        bool, Option(help="Author the membership despite failed checks")
    ] = False,
):
    """Add members to a compilation."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    resolved = [_resolve(m) for m in members]
    _check_members(db, source_id, slug, [sid for sid, _ in resolved], force)

    for offset, (member_id, member_slug) in enumerate(resolved):
        db.run_query(
            """
            INSERT INTO map_bounds.compilation_member
              (compilation_id, member_id, priority)
            VALUES (:compilation_id, :member_id, :priority)
            ON CONFLICT (compilation_id, member_id) DO UPDATE
              SET priority = coalesce(EXCLUDED.priority, compilation_member.priority)
            """,
            dict(
                compilation_id=source_id,
                member_id=member_id,
                priority=None if priority is None else priority + offset,
            ),
        )
        print(f"[green]+[/] {slug} <- {member_slug}")

    if reparent:
        for lyr, member in _reparent(db, source_id, [sid for sid, _ in resolved]):
            print(f"[red]-[/] {lyr} <- {member} [dim](now placed through {slug})[/]")
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
    assembly_mode: Annotated[str, Argument(help="topological | mosaic")],
):
    """Set how a compilation's members fit together.

    `topological` means they may overlap and the topology settles their extents
    by priority; `mosaic` means they partition the territory, so a member's
    extent is its footprint and its content is the compilation's inside it.
    Not derivable -- it is an assertion about the data.
    """
    if assembly_mode not in ("topological", "mosaic"):
        print("[red]Mode must be 'topological' or 'mosaic'[/]")
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
    apply: Annotated[
        bool, Option("--apply/--dry-run", help="Write the polygons")
    ] = False,
):
    """Give a compilation polygons of its own, clipped from its members'.

    Turns a virtual compilation into one that holds the assembled surface
    directly, so resolution stops at it instead of descending. Members keep
    their own polygons, so this is reversible with `dematerialize`.
    """
    db = get_database()
    source_id, slug = _resolve(compilation)
    _refuse_if_ingested(db, source_id, slug, "materialize")
    _refuse_if_materialized(db, source_id, slug)
    scale = db.run_query(
        "SELECT scale FROM maps.sources WHERE source_id = :id", dict(id=source_id)
    ).scalar()

    estimate = db.run_query(
        """
        WITH member AS (
          SELECT cm.member_id, cm.priority
          FROM map_bounds.compilation_member cm
          WHERE cm.compilation_id = :source_id
        ), covered_by AS (
          SELECT m.member_id, ST_Union(a.geometry) AS geometry
          FROM member m
          JOIN member higher ON higher.priority > m.priority
          JOIN map_bounds.map_area a ON a.source_id = higher.member_id
          GROUP BY m.member_id
        )
        SELECT
          count(*) AS polygons,
          count(*) FILTER (
            WHERE c.geometry IS NOT NULL AND ST_Intersects(p.geom, c.geometry)
          ) AS need_clipping
        FROM member m
        -- Wherever the member's content is: its own, or its mosaic parent's
        -- inside its footprint.
        CROSS JOIN LATERAL map_bounds.polygons_of(m.member_id) p
        LEFT JOIN covered_by c ON c.member_id = m.member_id
        """,
        dict(source_id=source_id),
    ).first()

    if not estimate or not estimate.polygons:
        print(f"[red]{slug}[/] has no member polygons to assemble")
        raise typer.Exit(1)

    print(
        f"[bold]{slug}[/] [dim]#{source_id}[/]: {estimate.polygons} polygons, "
        f"{estimate.need_clipping} needing clipping "
        f"({estimate.polygons - estimate.need_clipping} copied as-is)"
    )
    if not apply:
        print("[dim]Dry run. Pass --apply to write.[/]")
        return

    db.run_sql(
        proc("materialize-compilation"),
        dict(compilation_id=source_id, scale=scale),
    )
    db.session.commit()
    n = db.run_query(
        "SELECT count(*) FROM maps.polygons WHERE source_id = :id",
        dict(id=source_id),
    ).scalar()
    print(
        f"[green]{n}[/] polygons written."
        "\nRun [cyan]macrostrat topo update[/] so faces resolve to it rather"
        " than its members."
    )


@cli.command("dematerialize")
def dematerialize(
    compilation: Annotated[str, Argument(help="Slug or source id")],
):
    """Drop a compilation's derived polygons, returning it to virtual."""
    db = get_database()
    source_id, slug = _resolve(compilation)
    _refuse_if_ingested(db, source_id, slug, "dematerialize")
    n = db.run_query(
        "SELECT count(*) FROM maps.polygons WHERE source_id = :id", dict(id=source_id)
    ).scalar()
    db.run_sql(proc("dematerialize-compilation"), dict(compilation_id=source_id))
    db.session.commit()
    print(f"[green]{slug}[/]: {n} derived polygons removed; now virtual.")


@cli.command("lint")
def lint():
    """Report membership that has gone stale, without changing any of it.

    Everything here used to be handled by the layer sweep deleting edges on the
    next sync. Reporting is the whole point of the change: a map being superseded
    is news about the map, and what to do about it -- withdraw it, rank it down,
    leave it as a gap-filler -- is a judgment the sweep was making silently and
    unrecorded.
    """
    db = get_database()
    found = False

    stale = db.run_query(
        """
        SELECT c.slug AS compilation, s.slug AS member,
               sup.slug AS superseded_by,
               coalesce(s.geolayer, 'surface') AS member_geolayer,
               coalesce(c.geolayer, 'surface') AS compilation_geolayer,
               map_bounds.has_faces(c.source_id) AS compilation_is_layer,
               EXISTS (
                 SELECT 1 FROM map_bounds.map_area a
                 WHERE a.source_id = s.source_id
               ) AS has_boundary,
               EXISTS (
                 SELECT 1 FROM map_bounds.compilation_member x
                 WHERE x.compilation_id = s.source_id
               ) AS has_members
        FROM map_bounds.compilation_member cm
        JOIN maps.sources c ON c.source_id = cm.compilation_id
        JOIN maps.sources s ON s.source_id = cm.member_id
        LEFT JOIN maps.sources sup ON sup.source_id = s.superseded_by
        ORDER BY c.slug, s.slug
        """
    ).all()
    problems = []
    for r in stale:
        if r.superseded_by is not None:
            problems.append(
                (r.compilation, r.member, f"superseded by {r.superseded_by}")
            )
        if r.compilation_is_layer and r.member_geolayer != r.compilation_geolayer:
            problems.append(
                (
                    r.compilation,
                    r.member,
                    f"depicts {r.member_geolayer}, the layer depicts"
                    f" {r.compilation_geolayer}",
                )
            )
        if not r.has_boundary and not r.has_members:
            problems.append(
                (r.compilation, r.member, "no boundary -- holds no territory")
            )
    if problems:
        found = True
        table = Table(title="Members that no longer fit")
        table.add_column("Compilation")
        table.add_column("Member")
        table.add_column("Why")
        for comp, member, reason in problems:
            table.add_row(comp, member, f"[yellow]{reason}[/]")
        print(table)

    # A map placed both directly and through a compilation that is itself in the
    # same layer. Both routes resolve to the same map, the longer one wins on
    # depth, and the shorter one reads like a second opinion that was never meant.
    redundant = db.run_query(
        """
        SELECT layer.slug AS layer, member.slug AS member, parent.slug AS through
        FROM map_bounds.compilation_member direct
        JOIN map_bounds.compilation_member through
          ON through.compilation_id = direct.compilation_id
        JOIN map_bounds.compilation_member nested
          ON nested.compilation_id = through.member_id
         AND nested.member_id = direct.member_id
        JOIN maps.sources layer ON layer.source_id = direct.compilation_id
        JOIN maps.sources member ON member.source_id = direct.member_id
        JOIN maps.sources parent ON parent.source_id = through.member_id
        ORDER BY 1, 2
        """
    ).all()
    if redundant:
        found = True
        table = Table(title="Placed twice over")
        table.add_column("Layer")
        table.add_column("Member")
        table.add_column("Also through")
        for r in redundant:
            table.add_row(r.layer, r.member, r.through)
        print(table)
        print("[dim]`compilations rm <layer> <member>` keeps only the nested route.[/]")

    # Authored, assembled, and resolved nowhere. Reads `map_priority`, so it is
    # only meaningful after a sync.
    orphaned = db.run_query(
        """
        SELECT c.slug, count(DISTINCT cm.member_id) AS members
        FROM maps.sources c
        JOIN map_bounds.compilation_member cm ON cm.compilation_id = c.source_id
        WHERE NOT map_bounds.has_faces(c.source_id)
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.map_priority mp WHERE mp.member_id = c.source_id
          )
        GROUP BY 1 ORDER BY 1
        """
    ).all()
    if orphaned:
        found = True
        table = Table(title="Resolved in no layer")
        table.add_column("Compilation")
        table.add_column("Members", justify="right")
        for r in orphaned:
            table.add_row(r.slug, str(r.members))
        print(table)
        print("[dim]Expected for a compilation held deliberately out of service.[/]")

    if not found:
        print("[green]No problems found.[/]")


@cli.command("prune")
def prune(
    apply: Annotated[
        bool, Option("--apply/--dry-run", help="Write the changes")
    ] = False,
):
    """Withdraw members that hold nothing, from every compilation."""
    db = get_database()
    doomed = db.run_query(
        """
        SELECT c.slug AS compilation, s.slug AS member
        FROM map_bounds.compilation_member cm
        JOIN maps.sources c ON c.source_id = cm.compilation_id
        JOIN maps.sources s ON s.source_id = cm.member_id
        WHERE NOT EXISTS (
          SELECT 1 FROM map_bounds.map_area a WHERE a.source_id = cm.member_id
        )
        AND NOT EXISTS (
          SELECT 1 FROM map_bounds.compilation_member child
          WHERE child.compilation_id = cm.member_id
        )
        ORDER BY 1, 2
        """
    ).all()
    if not doomed:
        print("[green]Nothing to prune.[/]")
        return
    for r in doomed:
        print(f"[red]-[/] {r.compilation} <- {r.member}")
    if not apply:
        print(f"[yellow]{len(doomed)}[/] edges would be withdrawn [dim](--apply)[/]")
        return
    db.run_sql(proc("prune-compilation-members"))
    db.session.commit()
    print(f"[green]{len(doomed)}[/] edges withdrawn")


@cli.command("freeze-placements")
def freeze_placements(
    apply: Annotated[
        bool, Option("--apply/--dry-run", help="Write the changes")
    ] = False,
):
    """Check for layer placements the retired `scale` sweep left unwritten.

    Mostly a safety net, and usually a no-op. The sweep wrote ordinary
    `compilation_member` rows, and those persist, so any database that ever ran
    `compilations sync` or `topo update` under the old code already holds every
    placement it would have made -- there is no gap to fill.

    Not a migration, for the same reason. The one database where this writes
    anything is one with boundaries and layers that never ran the sweep at all,
    which is a database built fresh under authored membership -- exactly where
    placing every map by its scale is the behaviour being retired. Nothing in the
    database distinguishes that from a genuine upgrade, so the choice belongs to
    an operator who knows which one they have.

    Safe to repeat: it only adds a missing edge, and never rewrites the priority
    on one that already exists. Run it as a dry run when upgrading, to confirm
    nothing was left behind.
    """
    db = get_database()
    pending = db.run_query(
        """
        SELECT ml.slug AS layer, s.slug AS member, coalesce(s.new_priority, 0) AS priority
        FROM maps.sources s
        JOIN map_bounds.map_layer ml ON ml.slug = s.scale
        JOIN map_bounds.map_area a ON a.source_id = s.source_id
        WHERE s.scale IS NOT NULL
          AND ml.source_id IS NOT NULL
          AND coalesce(s.geolayer, 'surface') = 'surface'
          AND s.superseded_by IS NULL
          AND NOT map_bounds.is_mosaic_member(s.source_id)
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.compilation_member cm
            WHERE cm.member_id = s.source_id
              AND NOT map_bounds.has_faces(cm.compilation_id)
              AND NOT map_bounds.is_mosaic(cm.compilation_id)
          )
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.compilation_member cm
            WHERE cm.compilation_id = ml.source_id AND cm.member_id = s.source_id
          )
        ORDER BY 1, 2
        """
    ).all()
    if not pending:
        print("[green]Every placement is already authored.[/]")
        return
    for r in pending:
        print(f"[green]+[/] {r.layer} <- {r.member} [dim](priority {r.priority})[/]")
    if not apply:
        print(
            f"[yellow]{len(pending)}[/] placements would be written [dim](--apply)[/]"
        )
        return
    db.run_sql(proc("freeze-layer-placements"))
    db.session.commit()
    print(f"[green]{len(pending)}[/] placements written")


@cli.command("generate-carto-v1")
def generate_carto_v1(
    suffix: Annotated[str, Option(help="Suffix for the generated slugs")] = "v1",
    apply: Annotated[
        bool, Option("--apply/--dry-run", help="Write the changes")
    ] = False,
):
    """Freeze legacy carto's curatorial decisions as compilations.

    Reads `maps.sources.display_scales` -- legacy carto's membership list, which
    is compilation membership already, stored on the map instead of as edges --
    and writes it down in the model that replaced it. See `carto_v1.py` for what
    the tiers mean.

    Also runs as a migration, once, on any database that still has legacy carto
    content. This command is for inspecting the result and refreshing it by hand.

    The snapshot is not served. With no `map_layer` rows `sync-priority-paths`
    will not project its composition into the topology and nothing materializes
    faces for it; it exists to be inspected and diffed against what `carto`
    actually holds. Serving it later means adding layer rows and re-running
    `macrostrat topo update`, which is a second full face set.
    """
    db = get_database()
    tiers = carto_v1.plan(db, suffix)

    table = Table(title=f"Read out of display_scales (suffix `{suffix}`)")
    table.add_column("Compilation")
    table.add_column("Members", justify="right")
    for tier, members in tiers.items():
        table.add_row(carto_v1.slug_for(tier, suffix), str(len(members)))
    for tier in carto_v1.COMPOSITES:
        table.add_row(
            f"carto-{tier}-{suffix}",
            f"[dim]{carto_v1.slug_for(carto_v1.UNDER[tier], suffix)}"
            f" + {carto_v1.slug_for(tier, suffix)}[/]",
        )
    table.add_row(f"carto-{suffix}", "[dim]the three composites[/]")
    print(table)

    if not apply:
        print("[yellow]Nothing written[/] [dim](--apply)[/]")
        return

    # `write` commits its own work, so the migration path persists too.
    carto_v1.write(db, suffix, log=print)
    print(
        "\nRun [cyan]macrostrat topo update[/] to assemble their boundaries."
        "\n[dim]They are served nowhere until they are given map_layer rows.[/]"
    )
