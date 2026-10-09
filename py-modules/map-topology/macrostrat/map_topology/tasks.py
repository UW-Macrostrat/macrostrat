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
]
