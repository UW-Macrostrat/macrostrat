"""Usage-stats pipelines.

A pipeline picks its own records out of the shared access-log stream and owns
its own tables. The interface is deliberately small:

    name    — identifies the pipeline in `usage_stats.processed_logs`
    parse   — one log record in, one row out (or None to ignore it)
    write   — persist an object's worth of rows
    reset   — drop everything this pipeline has ingested

Plus a small reporting face, so `plot` works the same way for every pipeline:

    daily_series    — daily counts, as rows of {date, count, …}
    plot_label      — y-axis label for the figure
    plot_options    — extra CLI options this pipeline understands
    plot_omit_spikes — whether spike-cutting is the right default here

`parse` is called once per record per due pipeline, so it must be cheap: reject
on the narrowest test first (usually method or host) before doing any parsing.

Aggregation, where a pipeline does it, belongs inside `write` — it operates on
exactly one log object's rows, which is the unit the ingestion ledger records
and therefore the unit that must be written atomically.
"""

from typing import Protocol, runtime_checkable

from .rockd_dashboard import RockdDashboardPipeline
from .tileserver import TileserverPipeline


@runtime_checkable
class Pipeline(Protocol):
    name: str

    def parse(self, rec: dict) -> dict | None:
        """Extract a row from a log record, or None if the record isn't ours."""
        ...

    def write(self, db, rows: list[dict]) -> None:
        """Persist one log object's worth of rows. Called inside a transaction
        that also records the object in `processed_logs`."""
        ...

    def reset(self, db) -> str:
        """Delete everything this pipeline has ingested, so it can be rebuilt
        from the logs. Returns a human-readable summary of what was removed.
        Data that predates the log dumps and cannot be re-derived must be
        left alone."""
        ...

    # --- reporting ---------------------------------------------------------

    plot_label: str
    plot_options: frozenset  # extra `plot` options this pipeline accepts
    plot_omit_spikes: bool  # sensible default for --omit-spikes/--keep-spikes

    def daily_series(self, db, **options) -> list[dict]:
        """Daily counts for the plot: rows of {date, count}, optionally with a
        `new_system` lineage flag. Sorted by date."""
        ...


#: Every pipeline, by name. Values are factories rather than instances because
#: some need configuration injected (the Rockd pipeline needs the hashing salt).
PIPELINE_FACTORIES = {
    TileserverPipeline.name: lambda **kw: TileserverPipeline(),
    RockdDashboardPipeline.name: lambda *, client_salt, **kw: RockdDashboardPipeline(
        client_salt
    ),
}

PIPELINE_NAMES = tuple(PIPELINE_FACTORIES)


def get_pipelines(
    names: list[str] | None = None, *, client_salt: bytes | None = None
) -> list[Pipeline]:
    """Construct pipelines by name, defaulting to all of them.

    `client_salt` is required by the Rockd pipeline; omit it only when selecting
    pipelines that do not need it.
    """
    selected = list(names) if names else list(PIPELINE_NAMES)
    unknown = set(selected) - set(PIPELINE_FACTORIES)
    if unknown:
        raise ValueError(
            f"Unknown pipeline(s): {', '.join(sorted(unknown))}. "
            f"Available: {', '.join(PIPELINE_NAMES)}"
        )

    if client_salt is None and RockdDashboardPipeline.name in selected:
        raise ValueError(
            f"The {RockdDashboardPipeline.name!r} pipeline needs a client salt."
        )

    return [PIPELINE_FACTORIES[n](client_salt=client_salt) for n in selected]


__all__ = ["Pipeline", "PIPELINE_FACTORIES", "PIPELINE_NAMES", "get_pipelines"]
