"""Task-runner implementations of map-integration commands.

The specs are in `macrostrat.map_utils.tasks`. This package resolves its own
database through `get_database()` in many places; the run's connection is
placed in that context variable so every one of them -- and so a cancel, which
finds the run's sessions by name -- uses it.
"""

from macrostrat.database import Database


def run_process_pipeline(db: Database, params, ctx) -> dict:
    from macrostrat.core.database import db_ctx

    from .process import for_each_map, run_pipeline

    token = db_ctx.set(db)
    try:
        for_each_map(
            params.maps,
            run_pipeline,
            exclude=params.exclude or None,
            state=params.state,
            delete_existing=params.delete_existing,
            scale=params.scale,
            requires=None,
        )
    finally:
        db_ctx.reset(token)
    return {"maps": params.maps}
