"""Raster index tasks registered with the task runner.

The specs import nothing heavy, so the API can serve the catalog; the raster
libraries are imported when a task runs, on the admin worker.
"""

from pydantic import BaseModel, Field

from macrostrat.task_runner import RunContext, TaskSpec


class ScanParams(BaseModel):
    url: str = Field(
        min_length=1,
        title="Bucket prefix",
        description="An https:// or s3:// prefix, e.g. "
        "https://storage.example.org/bucket/prefix/",
    )
    mask_footprints: bool = Field(
        False,
        title="Mask footprints",
        description="Trace each footprint from the raster's validity mask rather "
        "than its bounding box. Reads every mask, so a large prefix takes a while.",
    )
    dry_run: bool = Field(
        False,
        title="Dry run",
        description="List what would be registered and change nothing.",
    )


def run_scan(db, params: ScanParams, ctx: RunContext) -> dict:
    from rich import print

    from macrostrat.raster_index import RasterIndex, scan_prefix

    objects = list(scan_prefix(params.url))
    if not objects:
        print(f"[yellow]No rasters found under {params.url}")
        return {"found": 0, "registered": 0, "failed": 0}

    if params.dry_run:
        for obj in objects:
            print(f"{obj.href} [dim]({obj.size / 1e6:.1f} MB)")
        print(f"[dim]{len(objects)} rasters (dry run: nothing registered)")
        return {"found": len(objects), "registered": 0, "failed": 0}

    index = RasterIndex(db.engine)
    registered, failed = 0, 0
    # One at a time rather than `add_rasters`, so each result reaches the output.
    for obj in objects:
        try:
            index.add_raster(obj.href, mask_footprint=params.mask_footprints)
        except Exception as err:
            failed += 1
            print(f"[red]{obj.href}: {err}")
        else:
            registered += 1
            print(obj.href)

    print(f"[green]Registered {registered}/{len(objects)} rasters")
    if failed:
        raise RuntimeError(f"{failed} of {len(objects)} rasters failed to register")
    return {"found": len(objects), "registered": registered, "failed": failed}


TASKS = [
    TaskSpec(
        name="rasters.scan",
        title="Find rasters",
        description="Register every raster under a bucket prefix. New rasters "
        "are unassigned until placed in a layer; ones already registered keep "
        "their layer and have their metadata refreshed.",
        params=ScanParams,
        run="macrostrat.raster_tasks:run_scan",
    ),
]
