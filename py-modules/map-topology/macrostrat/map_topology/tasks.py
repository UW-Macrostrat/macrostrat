"""Management tasks the topology registers with the task runner.

Light on purpose: the API serves this catalog, so the topology stack is imported
only when a task runs.
"""

from pydantic import BaseModel, Field

from macrostrat.task_runner import RunContext, TaskSpec


class UpdateParams(BaseModel):
    maps: list[str] = Field(
        default_factory=list,
        title="Maps",
        description="Map slugs, source ids or globs ('ngs-*'); none for every map.",
    )
    build_bounds: bool = Field(
        True,
        title="Build bounds first",
        description="Run `bounds build --all` before updating: quick, and only "
        "maps whose operations changed are rebuilt.",
    )
    bulk: bool = Field(
        False, title="Bulk", description="Re-node the selected maps from scratch."
    )
    one_at_a_time: bool = Field(
        False,
        title="One piece at a time",
        description="Node and commit each piece separately, reporting its time.",
    )
    piece_timeout: float | None = Field(
        None,
        title="Piece timeout (s)",
        description="Seconds before a piece is abandoned and recorded as failed; "
        "implies one at a time.",
    )


def run_update(db, params: UpdateParams, ctx: RunContext) -> dict:
    from rich import print

    from .bounds.build import build_all, describe
    from .manager import MacrostratTopologyManager
    from .topology import create_topo_context

    if params.build_bounds:
        print("[bold]Building stale bounds[/]")
        failures = 0
        for res in build_all(db):
            failures += bool(res.error)
            print(describe(res))
        if failures:
            raise RuntimeError(f"{failures} bounds failed to build")

    mgr = MacrostratTopologyManager(create_topo_context(db))
    summary = mgr.update_full(
        params.maps or None,
        bulk=params.bulk,
        one_at_a_time=params.one_at_a_time,
        piece_timeout=params.piece_timeout,
    )
    return summary.as_dict()


class StatusParams(BaseModel):
    pass


def run_status(db, params: StatusParams, ctx: RunContext) -> dict:
    from rich import print

    from .manager import (
        MacrostratTopologyManager,
        _print_map_info,
        get_maps_with_changed_geometries,
    )
    from .topology import create_topo_context

    mgr = MacrostratTopologyManager(create_topo_context(db))
    changed = get_maps_with_changed_geometries(mgr)
    if not changed:
        print("No maps with geometry changes")
    else:
        print(f"Found {len(changed)} maps with geometry changes")
        for row in changed:
            _print_map_info(row)
    return {"changed": len(changed)}


class LintParams(BaseModel):
    pass


class UnusedParams(BaseModel):
    targets: list[str] = Field(
        default_factory=list,
        title="Compilations or maps",
        description="Slugs, source ids or globs; every layer if empty.",
    )
    slivers: float | None = Field(
        None,
        ge=0,
        le=1,
        title="Slivers",
        description="Instead list maps whose faces show less than this share of "
        "their bounds (0.05). Reads every face geometry in scope.",
    )


def _as_command(db, command, **kwargs):
    """Run a `compilations` command function with the run's connection.

    The commands resolve the database through `get_database()`; the run's
    connection is placed in that context so they, and a cancel, use it. A
    non-zero `typer.Exit` is the command's failure.
    """
    import typer

    from macrostrat.core.database import db_ctx

    token = db_ctx.set(db)
    try:
        command(**kwargs)
    except typer.Exit as exit:
        if exit.exit_code:
            raise RuntimeError(f"exited with status {exit.exit_code}")
    finally:
        db_ctx.reset(token)


def run_lint(db, params: LintParams, ctx: RunContext) -> None:
    from .compilations import lint

    _as_command(db, lint)


def run_unused(db, params: UnusedParams, ctx: RunContext) -> None:
    from .compilations import unused

    _as_command(db, unused, targets=params.targets or None, slivers=params.slivers)


TASKS = [
    TaskSpec(
        name="topology.update",
        title="Update topology",
        description="The one command after any edit to maps, bounds or "
        "compilations: build stale bounds, node the maps whose bounds changed, "
        "recompile compilation bounds and priority paths, re-solve the faces "
        "whose owner changed, and rebuild member faces.",
        params=UpdateParams,
        run="macrostrat.map_topology.tasks:run_update",
    ),
    TaskSpec(
        name="topology.status",
        title="Topology status",
        description="List the maps whose geometry has changed since they were "
        "noded. Read-only.",
        params=StatusParams,
        run="macrostrat.map_topology.tasks:run_status",
    ),
    TaskSpec(
        name="compilations.lint",
        title="Lint compilations",
        description="Report membership that has gone stale: superseded members, "
        "members holding no territory, double placements. Read-only.",
        params=LintParams,
        run="macrostrat.map_topology.tasks:run_lint",
    ),
    TaskSpec(
        name="compilations.unused",
        title="Unused compilation members",
        description="List members that hold no face in a compilation they are "
        "ranked in; run after a topology update. Read-only.",
        params=UnusedParams,
        run="macrostrat.map_topology.tasks:run_unused",
    ),
]
