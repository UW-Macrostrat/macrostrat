"""Container entrypoint: `python -m usage_stats_service`.

argparse rather than Typer — this runs unattended from a CronJob, and a CLI
framework would be a dependency the worker has no use for. The interactive
command set (status, reset, plot) lives in the `usage_stats` Macrostrat CLI
subsystem, which is the other frontend over the same library.
"""

import sys
from argparse import ArgumentParser

from macrostrat.usage_stats_capture import PIPELINE_NAMES, capture, get_pipelines

from .config import ConfigError, client_salt, get_db, storage


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(
        prog="python -m usage_stats_service",
        description="Ingest access-log dumps from object storage into usage_stats.",
    )
    parser.add_argument(
        "--prefix",
        default="prod",
        help="Object-key prefix to scan. Defaults to production logs in every "
        "environment: a map of requests to a development cluster is close to "
        "useless, so development harvests production traffic too.",
    )
    parser.add_argument(
        "--pipeline",
        action="append",
        choices=PIPELINE_NAMES,
        help="Pipeline to run; repeatable. Defaults to all of them.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of new objects processed. Mostly for smoke tests.",
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-ingest objects already recorded for the selected pipelines. "
        "Note the tileserver aggregates accumulate, so this double-counts "
        "unless the pipeline is reset first.",
    )
    args = parser.parse_args(argv)

    try:
        pipelines = get_pipelines(args.pipeline, client_salt=client_salt())
        config = storage()
        db = get_db()
    except (ConfigError, ValueError) as err:
        # One line naming what to set, so a failing CronJob says why in its logs.
        print(f"error: {err}", file=sys.stderr)
        return 2

    print(f"Pipelines: {', '.join(p.name for p in pipelines)}")
    capture(
        db,
        config,
        pipelines,
        prefix=args.prefix,
        limit=args.limit,
        reprocess=args.reprocess,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
