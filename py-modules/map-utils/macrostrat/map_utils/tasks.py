"""Map tasks registered with the task runner.

The specs live here, GIS-free, so the API can serve the catalog and validate
parameters; the implementations are in `macrostrat.map_integration.tasks`,
which only the admin worker installs.
"""

from pydantic import BaseModel, Field

from macrostrat.task_runner import TaskSpec


class ProcessPipelineParams(BaseModel):
    maps: list[str] = Field(
        min_length=1,
        title="Maps",
        description="Map slugs, source ids or slug globs ('ngs-*').",
    )
    exclude: list[str] = Field(
        default_factory=list,
        title="Exclude",
        description="Slug globs to leave out of the selection.",
    )
    state: str | None = Field(
        None,
        title="Ingest state",
        description="Only maps whose ingest process is in this state ('ready').",
    )
    delete_existing: bool = Field(
        False,
        title="Delete existing",
        description="Replace a map's rows in the maps schema instead of keeping them.",
    )
    scale: str | None = Field(
        None,
        title="Scale",
        description="Insert at this scale rather than the source's own.",
    )


TASKS = [
    TaskSpec(
        name="maps.process-pipeline",
        title="Process maps",
        description="The post-ingestion pipeline for each selected map: copy to "
        "the maps schema, boundary from its polygons, legend, strat-name, unit "
        "and lith matching, lookup tables, and finalization. The same as "
        "`macrostrat maps process pipeline`.",
        params=ProcessPipelineParams,
        run="macrostrat.map_integration.tasks:run_process_pipeline",
    ),
]
