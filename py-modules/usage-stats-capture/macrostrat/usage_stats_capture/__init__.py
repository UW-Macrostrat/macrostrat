"""Log harvesting for Macrostrat usage statistics.

Pure library: pipelines and the ingest loop, with no configuration of its own
and no CLI. Callers supply a database, storage credentials and (for the Rockd
pipeline) a hashing salt, so the same logic serves both frontends — the
`usage-stats` service, configured from the environment, and the Macrostrat CLI,
configured from `macrostrat.toml`.
"""

from .harvest import capture, iter_log_records, latest_log_object
from .pipelines import PIPELINE_NAMES, Pipeline, get_pipelines
from .storage import S3Params

__all__ = [
    "PIPELINE_NAMES",
    "Pipeline",
    "S3Params",
    "capture",
    "get_pipelines",
    "iter_log_records",
    "latest_log_object",
]
