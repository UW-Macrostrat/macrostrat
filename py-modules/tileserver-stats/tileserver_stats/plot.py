"""Tileserver request-statistics figures for scientific reports.

Spare, professional matplotlib output (PDF / SVG / PNG, or inline in iTerm),
driven by tileserver_stats.day_index in the core Macrostrat database.

matplotlib and polars are heavy imports, so this module is imported lazily by
the `plot` CLI command rather than at package load.
"""

from __future__ import annotations

import base64
import io
import math
import os
import sys
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # headless: we render to a file or to an in-memory buffer

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.ticker import FuncFormatter

from macrostrat.core import get_database

from .params import Smoothing, resolve_date_window

SPIKE_QUANTILE = 0.80  # default: days above this quantile are treated as spikes


def fetch_daily_requests() -> pl.DataFrame:
    """Daily tile-request totals from day_index, split by pipeline lineage.

    Columns: date (Datetime), new_system (Boolean), count (Int64).
    """
    db = get_database()
    result = db.run_query(
        """
        SELECT date, new_system, sum(num_requests)::bigint AS count
        FROM tileserver_stats.day_index
        GROUP BY date, new_system
        ORDER BY date
        """
    )
    rows = [dict(r._mapping) for r in result]

    schema = {"date": pl.Datetime, "new_system": pl.Boolean, "count": pl.Int64}
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows, schema=schema)


def _filter_range(df: pl.DataFrame, time_range: str) -> pl.DataFrame:
    if df.is_empty():
        return df
    start, end = resolve_date_window(time_range, df["date"].max())
    if start is not None:
        df = df.filter(pl.col("date") >= start)
    if end is not None:
        df = df.filter(pl.col("date") < end)
    return df


def _prepare(
    df: pl.DataFrame, *, smooth_window: int, omit_spikes: bool, spike_quantile: float
) -> pl.DataFrame:
    """Collapse lineages to one daily series on a continuous timeline.

    Produces columns: date, is_spike, is_outage, series, band.
      - Missing days (outages) and spike days are left as nulls; the rolling mean
        skips them, so neither distorts the trend.
      - Outages remain gaps in `series`; spikes are flagged for dashed rendering.
    """
    daily = df.group_by("date").agg(pl.col("count").sum().alias("count")).sort("date")
    # Continuous daily timeline: gaps (outages) become explicit null rows.
    daily = daily.upsample(time_column="date", every="1d").with_columns(
        pl.col("count").is_null().alias("is_outage")
    )

    if omit_spikes:
        present = daily.filter(~pl.col("is_outage"))
        threshold = (
            present["count"].quantile(spike_quantile) if present.height else None
        )
        spike_expr = (
            (pl.col("count") > threshold) if threshold is not None else pl.lit(False)
        )
        daily = daily.with_columns(spike_expr.fill_null(False).alias("is_spike"))
    else:
        daily = daily.with_columns(pl.lit(False).alias("is_spike"))

    # `clean`: real daily counts, with outages and spikes left as NULL (not
    # interpolated or zero-filled). The rolling mean below skips nulls and
    # divides by the actual number of present days in each window — so gaps and
    # the edges of data drop-offs don't drag the average toward zero (which a
    # fixed window denominator would). `center=True` also avoids the lag that
    # smears a sharp step across the window.
    daily = daily.with_columns(
        pl.when(pl.col("is_spike") | pl.col("is_outage"))
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("count").cast(pl.Float64))
        .alias("clean")
    )

    if smooth_window > 1:
        daily = daily.with_columns(
            pl.col("clean")
            .rolling_mean(window_size=smooth_window, min_samples=1, center=True)
            .alias("series"),
            pl.col("clean")
            .rolling_std(window_size=smooth_window, min_samples=1, center=True)
            .alias("band"),
        )
    else:
        daily = daily.with_columns(
            pl.col("clean").alias("series"),
            pl.lit(None, dtype=pl.Float64).alias("band"),
        )

    # Outage days are gaps in the displayed line (the rolling mean would
    # otherwise bridge them from neighboring windows).
    return daily.with_columns(
        pl.when(pl.col("is_outage"))
        .then(pl.lit(None, dtype=pl.Float64))
        .otherwise(pl.col("series"))
        .alias("series")
    )


def _cutover_date(df: pl.DataFrame):
    """The legacy→new boundary: first new-system day, but only when both
    lineages are present (otherwise a cutover marker is meaningless)."""
    has_legacy = df.filter(~pl.col("new_system")).height > 0
    new = df.filter(pl.col("new_system"))
    if not has_legacy or new.height == 0:
        return None
    return new["date"].min()


def _nice_ceil(x: float) -> float:
    """Round up to a 'nice' number for axis limits (fine steps to avoid slack)."""
    if x <= 0:
        return 1.0
    exp = math.floor(math.log10(x))
    base = 10**exp
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8):
        if x <= m * base:
            return m * base
    return 10 * base


def _fmt_count(v: float, _pos=None) -> str:
    if v >= 1e6:
        return f"{v / 1e6:g}M"
    if v >= 1e3:
        return f"{v / 1e3:g}k"
    return f"{v:g}"


def _apply_report_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "figure.dpi": 150,
            "savefig.bbox": "tight",
        }
    )


def tileserver_stats_figure(
    out: Optional[Path] = None,
    *,
    log: bool = False,
    omit_spikes: bool = True,
    spike_quantile: float = SPIKE_QUANTILE,
    smoothing: Smoothing = Smoothing.weekly,
    time_range: str = "all",
) -> None:
    """Render the tile-requests-per-day figure.

    out=None prints inline to an iTerm console; otherwise the format follows the
    file suffix (.pdf / .svg / .png).
    """
    smooth_window = smoothing.window

    df = fetch_daily_requests()
    if df.is_empty():
        raise ValueError("No rows in tileserver_stats.day_index — nothing to plot.")
    df = _filter_range(df, time_range)
    if df.is_empty():
        raise ValueError(f"No data in the selected range ({time_range}).")

    daily = _prepare(
        df,
        smooth_window=smooth_window,
        omit_spikes=omit_spikes,
        spike_quantile=spike_quantile,
    )
    cutover = _cutover_date(df)

    dates = daily["date"].to_numpy()
    series = daily["series"].to_numpy()  # NaN at outages → the line breaks (gaps)
    band = daily["band"].to_numpy()
    is_spike = daily["is_spike"].to_numpy()

    _apply_report_style()
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ink = "#1b1b1b"

    if smooth_window > 1 and not np.all(np.isnan(band)):
        ax.fill_between(
            dates, series - band, series + band, color=ink, alpha=0.12, lw=0
        )

    # Solid for real data (breaks at spikes and at outage gaps); dashed across
    # interpolated spike runs so cut scrapes read differently from outages.
    solid = np.where(is_spike, np.nan, series)
    ax.plot(dates, solid, "-", color=ink, lw=1.0)
    if is_spike.any():
        spike_adj = is_spike.copy()
        spike_adj[:-1] |= is_spike[1:]
        spike_adj[1:] |= is_spike[:-1]
        dashed = np.where(spike_adj, series, np.nan)
        ax.plot(dates, dashed, "--", color=ink, lw=0.9, dashes=(3, 2))

    # Subtle cutover marker: a thin dashed rule with a small label.
    if cutover is not None:
        ax.axvline(cutover, color="#999999", lw=0.8, ls=(0, (2, 2)), zorder=0)
        ax.annotate(
            "new pipeline",
            xy=(cutover, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(3, -8),
            textcoords="offset points",
            fontsize=7,
            color="#777777",
            ha="left",
            va="top",
        )

    # Size the y-axis to the real (non-spike) signal so de-emphasized scrapes
    # don't inflate the bounds; tight padding + fine "nice" steps.
    real = np.isfinite(series) & ~is_spike
    envelope = (series + np.nan_to_num(band, nan=0.0))[real]
    if not envelope.size:  # e.g. --keep-spikes leaves nothing flagged
        envelope = (series + np.nan_to_num(band, nan=0.0))[np.isfinite(series)]
    ymax = _nice_ceil(float(envelope.max()) * 1.02) if envelope.size else 1.0
    if log:
        ax.set_yscale("log")
        lo_vals = series[real & (series > 0)]
        lo = float(lo_vals.min()) if lo_vals.size else 1.0
        ax.set_ylim(10 ** math.floor(math.log10(lo)), ymax)
    else:
        ax.set_ylim(0, ymax)

    # Spare styling: no top/right frame, light dotted y-grid, year ticks.
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, axis="y", linestyle=":", linewidth=0.5, color="#cccccc")
    ax.yaxis.set_major_formatter(FuncFormatter(_fmt_count))
    # Adaptive date ticks: AutoDateLocator picks a sensible interval for the
    # visible span (years / months / days) and ConciseDateFormatter labels them
    # compactly (the higher unit shown once, as an offset), so the axis reads
    # well whether the range is a decade, a single year, or a month.
    locator = mdates.AutoDateLocator(minticks=4, maxticks=9)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlim(dates.min(), dates.max())

    smoothing = f"{smooth_window}-day mean" if smooth_window > 1 else "daily"
    ax.set_ylabel(f"Tile requests per day ({smoothing})")

    fig.tight_layout()

    if out is None:
        _print_inline(fig)
    else:
        out = Path(out)
        fig.savefig(out)  # format inferred from suffix
        print(f"Wrote {out}")
    plt.close(fig)


def _print_inline(fig) -> None:
    """Print the figure into the terminal. Uses the iTerm2 inline-image protocol;
    falls back to writing a PNG when not in iTerm."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    in_iterm = (
        os.environ.get("TERM_PROGRAM") == "iTerm.app"
        or "ITERM_SESSION_ID" in os.environ
    )
    if in_iterm:
        payload = base64.b64encode(buf.getvalue()).decode()
        sys.stdout.write(f"\033]1337;File=inline=1;width=100%:{payload}\a\n")
        sys.stdout.flush()
    else:
        fallback = Path("tileserver-stats.png")
        fallback.write_bytes(buf.getvalue())
        print(f"Not an iTerm console; wrote {fallback} instead.")
