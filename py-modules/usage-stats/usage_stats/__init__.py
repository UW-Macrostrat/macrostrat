import asyncio
import random
from pathlib import Path
from typing import Optional

from rich import print
from typer import BadParameter, Option, Typer, confirm

from macrostrat.core import get_database
from macrostrat.core.config import settings
from macrostrat.database import Database
from macrostrat.database.transfer import move_tables

from .harvest import (
    capture,
    iter_log_records,
    latest_log_object,
    resolve_access_logs_config,
)
from .params import Smoothing, is_valid_range
from .pipelines import PIPELINES, get_pipelines
from .pipelines.tileserver import parse_tile_path

here = Path(__file__).parent

app = Typer(no_args_is_help=True, short_help="Compile Macrostrat usage statistics")


def _resolve(pipeline: Optional[list[str]]):
    try:
        return get_pipelines(pipeline)
    except ValueError as err:
        raise BadParameter(str(err), param_hint="--pipeline")


@app.command(name="capture")
def capture_command(
    prefix: str = Option("prod", "--prefix", help="Object-key prefix to scan."),
    pipeline: Optional[list[str]] = Option(
        None,
        "--pipeline",
        "-p",
        help="Pipeline(s) to run. Repeatable; defaults to all of them.",
    ),
    limit: Optional[int] = Option(
        None, "--limit", help="Cap the number of new objects processed."
    ),
    reprocess: bool = Option(
        False,
        "--reprocess",
        help="Re-ingest objects already recorded for the selected pipeline(s).",
    ),
):
    """Ingest access-log dumps from object storage into the usage_stats schema.

    Each log object is read once and fed to every selected pipeline that hasn't
    already processed it, so running all pipelines together costs one pass, not
    one per pipeline.

    Idempotent and resumable: objects are recorded per pipeline in
    usage_stats.processed_logs and skipped on later runs. --reprocess overrides
    that; note the tileserver aggregates accumulate on conflict, so reprocessing
    them double-counts unless `reset` is run first.
    """
    config = resolve_access_logs_config()
    pipelines = _resolve(pipeline)
    print(f"Pipelines: {', '.join(p.name for p in pipelines)}\n")
    capture(config, pipelines, prefix=prefix, limit=limit, reprocess=reprocess)


@app.command(name="status")
def status_command():
    """Show ingestion progress per pipeline."""
    db = get_database()
    rows = db.run_query(
        """
        SELECT pipeline,
               count(*) AS n_objects,
               sum(num_matched) AS n_matched,
               min(object_name) AS first_object,
               max(object_name) AS last_object
        FROM usage_stats.processed_logs
        GROUP BY pipeline
        ORDER BY pipeline
        """
    ).mappings()

    any_rows = False
    for row in rows:
        any_rows = True
        print(f"[bold]{row['pipeline']}[/]")
        print(f"  objects processed: {row['n_objects']}")
        print(f"  records matched:   {row['n_matched']}")
        print(f"  range:             {row['first_object']} … {row['last_object']}")

    if not any_rows:
        print("No log objects have been processed yet.")
        return

    known = {p.name for p in PIPELINES}
    print(f"\n[dim]Registered pipelines: {', '.join(sorted(known))}[/]")


@app.command(name="plot")
def plot_command(
    out: Optional[Path] = Option(
        None,
        "--out",
        "-o",
        help="Output file (.pdf/.svg/.png). Omit to print inline (iTerm).",
    ),
    smooth: Smoothing = Option(
        Smoothing.weekly,
        "--smooth",
        help="Smoothing: none (raw daily), weekly (7-day mean), monthly (30-day mean).",
    ),
    range_: str = Option(
        "all",
        "--range",
        help="Time window: last-month, last-year, last-5-years, all, or a "
        "4-digit calendar year (e.g. 2026).",
    ),
    log: bool = Option(False, "--log/--linear", help="Logarithmic vs. linear y-axis."),
    omit_spikes: bool = Option(
        True,
        "--omit-spikes/--keep-spikes",
        help="Cut spike days before smoothing; drawn dashed.",
    ),
    skip_bots: bool = Option(
        False,
        "--skip-bots/--keep-bots",
        help="Exclude known automated clients (is_bot) so the plot reflects "
        "organic traffic only.",
    ),
    spike_quantile: Optional[float] = Option(
        None,
        "--spike-quantile",
        help="Daily-count quantile above which days are treated as spikes "
        "(default: module SPIKE_QUANTILE).",
    ),
):
    """Plot tile requests per day for reports."""
    if not is_valid_range(range_):
        raise BadParameter(
            "Use last-month, last-year, last-5-years, all, or a 4-digit year "
            "(e.g. 2026).",
            param_hint="--range",
        )

    from .plot import SPIKE_QUANTILE, tileserver_stats_figure

    tileserver_stats_figure(
        out,
        log=log,
        omit_spikes=omit_spikes,
        spike_quantile=SPIKE_QUANTILE if spike_quantile is None else spike_quantile,
        smoothing=smooth,
        time_range=range_,
        skip_bots=skip_bots,
    )


@app.command(name="show-sample")
def show_sample(
    path: Optional[str] = Option(
        None,
        "--path",
        "-p",
        help="S3 object key of a log file. Default: the most recent upload.",
    ),
    count: int = Option(20, "--count", "-n", help="Number of URLs to sample."),
    all_requests: bool = Option(
        False,
        "--all",
        help="Sample all requests, not just tile requests.",
    ),
    prefix: str = Option(
        "prod", "--prefix", help="Object-key prefix to search for the latest log."
    ),
):
    """Print a random sample of request URLs from a log file — for diagnosing
    what is (and isn't) being captured. Defaults to the most recently uploaded
    log object; pass --path to target a specific one, or --all to include
    non-tile requests."""
    config = resolve_access_logs_config()
    s3 = config.get_client()

    object_name = path or latest_log_object(s3, config.bucket, prefix)
    if object_name is None:
        print(f"No .zst log objects found under {prefix!r}.")
        return
    print(f"Sampling from [bold]{object_name}[/]\n")

    urls = []
    n_lines = 0
    for rec in iter_log_records(s3, config.bucket, object_name):
        n_lines += 1
        if rec.get("RequestMethod") != "GET":
            continue
        request_path = rec.get("RequestPath")
        if not request_path:
            continue
        if not all_requests and parse_tile_path(request_path) is None:
            continue
        urls.append(f"{rec.get('RequestHost', '')}{request_path}")

    if not urls:
        print("No matching requests found.")
        return

    for url in random.sample(urls, min(count, len(urls))):
        print(url)

    kind = "requests" if all_requests else "tile requests"
    print(
        f"\n[dim]{min(count, len(urls))} of {len(urls)} {kind} "
        f"({n_lines} log lines)[/]"
    )


@app.command(name="reset", rich_help_panel="Development")
def reset_command(
    pipeline: Optional[list[str]] = Option(
        None,
        "--pipeline",
        "-p",
        help="Pipeline(s) to reset. Repeatable; defaults to all of them.",
    ),
    yes: bool = Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
):
    """Drop a pipeline's ingested data and its processed-log records, so the log
    dumps can be re-ingested from scratch.

    Only touches data derived from the log dumps — the tileserver pipeline's
    legacy lineage (new_system = false, back to 2018) has no surviving source
    and is always preserved. For development, and for rebuilding after a change
    to parsing or filter logic.
    """
    pipelines = _resolve(pipeline)
    db = get_database()

    names = ", ".join(p.name for p in pipelines)
    if not yes:
        confirm(
            f"Delete all ingested data and processed-log records for: {names}?",
            abort=True,
        )

    with db.transaction():
        for p in pipelines:
            summary = p.reset(db)
            n_log = db.run_query(
                "DELETE FROM usage_stats.processed_logs WHERE pipeline = :name",
                {"name": p.name},
            ).rowcount
            print(f"{p.name}: cleared {summary}; {n_log} processed-log rows")


@app.command(name="migrate-old", rich_help_panel="Development")
def migrate_data(drop: bool = False):
    """Merge the standalone tileserver_stats database into the core Macrostrat database."""
    tileserver_db = settings.databases.get("tileserver_stats")
    print(f"Connecting to {tileserver_db}")
    if not tileserver_db:
        print("No tileserver_stats database configured; nothing to do.")
        return

    tdb = Database(tileserver_db)
    # Rename the schema stats to tileserver_stats
    tdb.run_sql("ALTER SCHEMA stats RENAME TO tileserver_stats")

    # Move the `requests` table into the `tileserver_stats` schema
    tdb.run_sql("ALTER TABLE requests SET SCHEMA tileserver_stats")

    # Switch to SQL in Macrostrat database
    db = get_database()
    # Merge the `tileserver_stats` schema into the core Macrostrat database

    task = move_tables(tdb.engine, db.engine, schemas=["tileserver_stats"])
    asyncio.run(task)


def build_schema_config():
    from macrostrat.schema_management.composer import SchemaDefinition

    main_def = SchemaDefinition(
        name="usage-stats",
        depends_on=["public"],
        provides=[
            here / "schema" / "usage-stats.sql",
        ],
        environments=frozenset({"local", "development", "production"}),
        owner="macrostrat",
    )

    legacy = SchemaDefinition(
        name="tileserver-stats-legacy",
        depends_on=["usage-stats"],
        provides=[here / "schema" / "tileserver-stats.legacy.sql"],
        environments=frozenset({"development", "production"}),
        owner="macrostrat",
    )

    return [main_def, legacy]
