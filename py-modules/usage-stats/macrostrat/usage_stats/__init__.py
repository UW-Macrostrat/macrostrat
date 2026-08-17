"""Interactive frontend for the usage-stats harvester.

The harvesting itself lives in `usage_stats_capture`: a plain library with no
CLI framework and no Macrostrat configuration, so it deploys as a small
container. This package is the *other* frontend over the same functions — a
Typer CLI, figures, and configuration read from `macrostrat.toml`.

Configuration bridging runs at import: values from `macrostrat.toml` are pushed
into the `USAGE_STATS_*` environment variables the library reads. The direction
matters — the library never reaches into Macrostrat configuration.
"""

import random
from pathlib import Path
from typing import Optional

from rich import print
from typer import BadParameter, Option, Typer, confirm
from macrostrat.usage_stats_capture import (
    PIPELINE_NAMES,
    S3Params,
    capture,
    get_pipelines,
    iter_log_records,
    latest_log_object,
)
from macrostrat.usage_stats_capture.pipelines.rockd_dashboard import DEDUP_RELATIONS
from macrostrat.usage_stats_capture.pipelines.tileserver import parse_tile_path

from .params import Smoothing, is_valid_range

here = Path(__file__).parent

app = Typer(no_args_is_help=True, short_help="Compile Macrostrat usage statistics")


def _setting(*path):
    """Look a value up in macrostrat.toml, tolerating the shapes its nested
    config can take."""
    from macrostrat.core.config import settings

    value = settings
    for key in path:
        try:
            value = value[key]
        except (KeyError, TypeError, AttributeError):
            try:
                value = getattr(value, key)
            except AttributeError:
                return None
        if value is None:
            return None
    return value


def get_db():
    """The Macrostrat database, as the CLI's other subsystems see it."""
    from macrostrat.core import get_database

    return get_database()


def _storage() -> S3Params:
    """Access-log storage credentials from macrostrat.toml."""
    # The section is spelled either way in the wild.
    for section in ("access-logs", "access_logs"):
        fields = {
            field: _setting("storage", section, field)
            for field in ("bucket", "endpoint", "access_key", "secret_key")
        }
        if all(fields.values()):
            return S3Params(**fields)
    raise BadParameter(
        "storage.access-logs is not configured in macrostrat.toml.",
        param_hint="configuration",
    )


def _client_salt() -> bytes:
    """Hashing salt from macrostrat.toml, or derived from the app secret.

    Deriving it means local use needs no extra configuration; the derivation is
    domain-separated so the result can't be used against anything else keyed on
    that secret.
    """
    explicit = _setting("usage_stats_client_salt")
    if explicit:
        return str(explicit).encode()

    secret = _setting("secret_key")
    if secret:
        from hashlib import blake2b

        return blake2b(
            str(secret).encode(), person=b"usage-stats", digest_size=32
        ).digest()

    raise BadParameter(
        "Set `usage_stats_client_salt` (or `secret_key`) in macrostrat.toml. "
        "Changing it later forks client_id and breaks deduplication.",
        param_hint="configuration",
    )


def _resolve(pipeline: Optional[list[str]]):
    try:
        return get_pipelines(pipeline, client_salt=_client_salt())
    except ValueError as err:
        raise BadParameter(str(err), param_hint="--pipeline")


@app.command(name="capture")
def capture_command(
    prefix: str = Option(
        "prod",
        "--prefix",
        help="Object-key prefix to scan. Defaults to production logs in EVERY "
        "environment: a map of requests to the development cluster is close to "
        "useless, so development harvests production traffic too.",
    ),
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
    config = _storage()
    pipelines = _resolve(pipeline)
    print(f"Pipelines: {', '.join(p.name for p in pipelines)}\n")
    capture(
        get_db(), config, pipelines, prefix=prefix, limit=limit, reprocess=reprocess
    )


@app.command(name="status")
def status_command():
    """Show ingestion progress per pipeline."""
    db = get_db()
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

    known = set(PIPELINE_NAMES)
    print(f"\n[dim]Registered pipelines: {', '.join(sorted(known))}[/]")


@app.command(name="plot")
def plot_command(
    pipeline: str = Option(
        "tileserver",
        "--pipeline",
        "-p",
        help="Which pipeline's daily series to plot.",
    ),
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
    omit_spikes: Optional[bool] = Option(
        None,
        "--omit-spikes/--keep-spikes",
        help="Cut spike days before smoothing; drawn dashed. Defaults per "
        "pipeline — on for tileserver (scrapes), off for rockd-dashboard "
        "(where spikes are real usage).",
    ),
    skip_bots: bool = Option(
        False,
        "--skip-bots/--keep-bots",
        help="[tileserver] Exclude known automated clients (is_bot) so the plot "
        "reflects organic traffic only.",
    ),
    dedup: str = Option(
        "raw",
        "--dedup",
        help="[rockd-dashboard] Which series to count: raw (every request), "
        "views (250 m / 15 min), sessions (500 m / 1 h).",
    ),
    spike_quantile: Optional[float] = Option(
        None,
        "--spike-quantile",
        help="Daily-count quantile above which days are treated as spikes "
        "(default: module SPIKE_QUANTILE).",
    ),
):
    """Plot a pipeline's daily counts for reports."""
    if not is_valid_range(range_):
        raise BadParameter(
            "Use last-month, last-year, last-5-years, all, or a 4-digit year "
            "(e.g. 2026).",
            param_hint="--range",
        )

    if dedup not in DEDUP_RELATIONS:
        raise BadParameter(
            f"Choose from: {', '.join(DEDUP_RELATIONS)}.", param_hint="--dedup"
        )

    target = _resolve([pipeline])[0]

    # Pipeline-specific options are rejected rather than silently ignored, so a
    # flag that can't do anything is an error instead of a misleading figure.
    requested = {"skip_bots": skip_bots, "dedup": dedup != "raw"}
    for name, was_set in requested.items():
        if was_set and name not in target.plot_options:
            raise BadParameter(
                f"--{name.replace('_', '-')} does not apply to the "
                f"{target.name!r} pipeline.",
                param_hint=f"--{name.replace('_', '-')}",
            )

    options = {}
    if "skip_bots" in target.plot_options:
        options["skip_bots"] = skip_bots
    if "dedup" in target.plot_options:
        options["dedup"] = dedup

    from .plot import SPIKE_QUANTILE, usage_stats_figure

    usage_stats_figure(
        target,
        out,
        log=log,
        omit_spikes=omit_spikes,
        spike_quantile=SPIKE_QUANTILE if spike_quantile is None else spike_quantile,
        smoothing=smooth,
        time_range=range_,
        **options,
    )


@app.command(name="migrate-old", rich_help_panel="Development")
def migrate_data(drop: bool = False):
    """Merge the standalone tileserver_stats database into the core Macrostrat
    database. Legacy one-off, kept for reference."""
    import asyncio

    from macrostrat.core import get_database
    from macrostrat.core.config import settings
    from macrostrat.database import Database
    from macrostrat.database.transfer import move_tables

    tileserver_db = settings.databases.get("tileserver_stats")
    print(f"Connecting to {tileserver_db}")
    if not tileserver_db:
        print("No tileserver_stats database configured; nothing to do.")
        return

    tdb = Database(tileserver_db)
    tdb.run_sql("ALTER SCHEMA stats RENAME TO tileserver_stats")
    tdb.run_sql("ALTER TABLE requests SET SCHEMA tileserver_stats")

    db = get_database()
    asyncio.run(move_tables(tdb.engine, db.engine, schemas=["tileserver_stats"]))


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
    config = _storage()
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
    db = get_db()

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


def _schema_dir() -> Path:
    """Where the schema SQL lives — in the capture package, beside the pipelines
    that write those tables."""
    import macrostrat.usage_stats_capture as capture_pkg

    return Path(capture_pkg.__file__).parent / "schema"


def build_schema_config():
    """Schema chunks for the usage_stats schema.

    The SQL lives with the pipelines that write those tables, in
    `usage_stats_capture`; this only registers it with the schema builder.
    """
    from macrostrat.schema_management.composer import SchemaDefinition

    main_def = SchemaDefinition(
        name="usage-stats",
        depends_on=["public"],
        provides=[
            _schema_dir() / "usage-stats.sql",
        ],
        environments=frozenset({"local", "development", "production"}),
        owner="macrostrat",
    )

    legacy = SchemaDefinition(
        name="tileserver-stats-legacy",
        depends_on=["usage-stats"],
        provides=[_schema_dir() / "tileserver-stats.legacy.sql"],
        environments=frozenset({"development", "production"}),
        owner="macrostrat",
    )

    return [main_def, legacy]
