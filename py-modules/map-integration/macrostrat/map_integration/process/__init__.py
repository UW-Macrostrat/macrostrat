"""
Map processing pipeline (v2)

+ macrostrat process rgeom <source_id>
+ macrostrat process web_geom <source_id>
+ macrostrat process legend <source_id>
+ macrostrat match strat_names <source_id>
+ macrostrat match units <source_id>
+ macrostrat match liths <source_id>
+ macrostrat process burwell_lookup <source_id>
+ macrostrat process legend_lookup <source_id>
+ macrostrat process carto <source_id>
+ macrostrat process carto_lines <source_id>
+ macrostrat seed <source_id>

"""

import re
from typing import Annotated, Optional

from rich import print
from typer import Argument, Exit, Option

from macrostrat.core.exc import MacrostratError

from ..database import get_database, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..utils import IngestionCLI
from ..utils.map_info import (
    MapInfo,
    MapSelector,
    has_map_schema_data,
    resolve_maps,
)
from .geometry import create_rgeom, create_webgeom
from .insert import copy_to_maps, run_insert
from .legend_lookup import legend_lookup
from .lookup import make_lookup
from .status import processing_status

cli = IngestionCLI(
    no_args_is_help=True, name="process", help="Process map data once ingested"
)

cli.add_command(processing_status, name="status")


def for_each_map(selectors, step, **kwargs):
    """Run a single-map processing step over every selected map.

    Every step in this module takes a `MapInfo` first and options after, so one
    adapter covers all of them. Failures are collected rather than aborting the
    sweep: over 114 maps, stopping on the first bad one wastes the rest of the
    run, and the summary says which to look at.
    """
    db = get_database()
    maps = resolve_maps(db, selectors)
    many = len(maps) > 1
    if many:
        print(f"[dim]{len(maps)} maps[/]")

    failed = []
    for m in maps:
        if many:
            print(f"[bold cyan]{m.slug}[/] [dim]#{m.id}[/]")
        try:
            step(m, **kwargs)
        except Exception as err:  # noqa: BLE001 -- reported per map, see above
            if not many:
                raise
            failed.append((m.slug, str(err).strip().splitlines()[0]))
            print(f"  [red]failed[/] {failed[-1][1]}")

    if failed:
        print(f"\n[red]{len(failed)} of {len(maps)} failed[/]")
        for slug, err in failed:
            print(f"  [red]{slug}[/] {err}")
        raise MacrostratError(f"{len(failed)} maps failed")


def run_pipeline(source: MapInfo, delete_existing: bool = False, scale: str = None):
    """Run the full post-ingestion pipeline for one map source."""
    try:
        copy_to_maps(
            get_database(), source, delete_existing=delete_existing, scale=scale
        )
    except ValueError as e:
        print(e)
        if not delete_existing:
            print("Continuing with existing map data")
    run_legend(source)
    match_strat_names(source)
    match_units(source)
    match_liths(source)
    make_lookup(source)
    legend_lookup(source)
    finalize_one(source)


@cli.command(name="pipeline")
def pipeline(maps: MapSelector, delete_existing: bool = False, scale: str = None):
    """
    Run the full post-pipeline for the selected map sources

    This includes:
    - Copy to maps schema
    - Legend lookup table generation
    - Match strat names
    - Match units
    - Match liths
    - Make lookup
    """
    for_each_map(maps, run_pipeline, delete_existing=delete_existing, scale=scale)


def run_legend(map: MapInfo):
    """Update legend lookup tables for one map source."""
    db = get_database()
    proc = sql_file("update-legend")
    db.run_sql(proc, {"source_id": map.id})


@cli.command(name="rgeom", rich_help_panel="Sources")
def rgeom(maps: MapSelector):
    """Compose reference geometries for the selected map sources."""
    for_each_map(maps, create_rgeom)


@cli.command(name="web-geom", rich_help_panel="Sources")
def web_geom(maps: MapSelector, legacy: bool = False):
    """Create simplified web geometries for the selected map sources."""
    for_each_map(maps, create_webgeom, legacy=legacy)


@cli.command(name="insert", rich_help_panel="Map")
def insert(
    maps: MapSelector,
    delete_existing: bool = False,
    scale: str = None,
    staging_prefix: Annotated[
        Optional[str],
        Option(
            "--staging-prefix",
            help="Name the sources.<prefix>_* staging tables (default: the slug)",
        ),
    ] = None,
    allow_unattributed: Annotated[
        bool,
        Option(
            "--allow-unattributed",
            help="Insert even though lith/t_interval/b_interval are entirely null",
        ),
    ] = False,
):
    """Copy staged data to the maps schema for the selected map sources.

    A compilation whose members share one staging table passes it once:
    `insert 'ngs-*' --staging-prefix ngs` covers all 114.
    """
    for_each_map(
        maps,
        run_insert,
        delete_existing=delete_existing,
        scale=scale,
        staging_prefix=staging_prefix,
        allow_unattributed=allow_unattributed,
    )


@cli.command(name="legend", rich_help_panel="Map")
def legend(maps: MapSelector):
    """Update legend lookup tables for the selected map sources."""
    for_each_map(maps, run_legend)


@cli.command(name="strat-names", rich_help_panel="Matching")
def strat_names(
    maps: MapSelector,
    field: str = Option(None, help="Match only on this legend field (e.g. descrip)"),
):
    """Match the selected map sources to Macrostrat stratigraphic names."""
    from functools import partial

    for_each_map(maps, partial(match_strat_names, fields=_match_fields(field)))


@cli.command(name="units", rich_help_panel="Matching")
def units(maps: MapSelector):
    """Match the selected map sources to Macrostrat units."""
    for_each_map(maps, match_units)


@cli.command(name="liths", rich_help_panel="Matching")
def liths(maps: MapSelector):
    """Match the selected map sources to Macrostrat lithologies."""
    for_each_map(maps, match_liths)


@cli.command(name="lookup", rich_help_panel="Lookup")
def lookup(maps: MapSelector):
    """Refresh the lookup tables for the selected map sources."""
    for_each_map(maps, make_lookup)


@cli.command(name="legend-lookup", rich_help_panel="Lookup")
def legend_lookup_cmd(maps: MapSelector):
    """Refresh legend lookup tables for the selected map sources."""
    for_each_map(maps, legend_lookup)


def _match_fields(field: str | None) -> tuple:
    """Resolve a `--field` option to the tuple of legend columns to read."""
    from ..match.strat_names import FIELD_TIERS

    if field is None:
        return FIELD_TIERS
    if field not in FIELD_TIERS:
        raise MacrostratError(
            f"{field!r} is not a legend text field",
            details="Choose one of: " + ", ".join(FIELD_TIERS),
        )
    return (field,)


@cli.command(name="strat-names-report", rich_help_panel="Lookup")
def strat_names_report(
    pattern: str = Argument(..., help="Source slug or SQL LIKE pattern, e.g. `ngs-%`"),
    examples: int = Option(4, help="Lost/gained examples to print per source"),
    field: str = Option(None, help="Match only on this legend field (e.g. descrip)"),
    examples_from: str = Option(
        None,
        "--examples-from",
        help="Show worked examples of matches from this field instead of the"
        " lost/gained lists. Matching is unaffected.",
    ),
    full_text: bool = Option(
        False,
        "--full-text",
        help="Print the whole source text of each example, with the matched"
        " names highlighted. A description match cannot be judged without it.",
    ),
):
    """Score the prototype matcher against what the current pipeline produced.

    Read-only. Writes nothing and touches no pipeline table -- it reports what a
    legend-grain matcher *would* find, beside `maps.legend.strat_name_ids` as it
    stands, so the two can be compared before anything is replaced.

    SGMC is the benchmark: clean legend text, 96.7% matched by the current
    twelve-pass pipeline. Reaching that is the bar for adopting this on NGS.
    """
    from rich.table import Table

    from ..match.strat_names import (
        FIELD_TIERS,
        prepare,
        report_for_source,
        sources_matching,
    )

    db = get_database()
    print("[dim]Normalizing the lexicon[/]")
    lexicon = prepare(db)

    slugs = sources_matching(db, pattern)
    if not slugs:
        print(f"[red]No sources with legend rows match[/] {pattern}")
        raise Exit(1)

    table = Table(title=f"Prototype vs current ({pattern})")
    for col in ("Source", "Rows", "Current", "Proposed", "Lost", "Gained", "Gaps"):
        table.add_column(col, justify="right" if col != "Source" else "left")

    totals = dict(
        rows=0,
        current=0,
        proposed=0,
        lost=0,
        gained=0,
        pairs_current=0,
        pairs_proposed=0,
        pairs_kept=0,
        concepts_current=0,
        concepts_proposed=0,
    )
    all_gaps: set = set()
    all_basis: dict = {}
    all_tiers: dict = {}
    reports = []
    for slug in slugs:
        rep = report_for_source(db, slug, lexicon, fields=_match_fields(field))
        reports.append(rep)
        totals["rows"] += rep.rows
        totals["current"] += rep.current
        totals["proposed"] += rep.proposed
        totals["lost"] += len(rep.lost)
        totals["gained"] += len(rep.gained)
        for k in (
            "pairs_current",
            "pairs_proposed",
            "pairs_kept",
            "concepts_current",
            "concepts_proposed",
        ):
            totals[k] += getattr(rep, k)
        all_gaps |= rep.lexicon_gaps
        for basis, n in rep.by_basis.items():
            all_basis[basis] = all_basis.get(basis, 0) + n
        for tier, n in rep.by_tier.items():
            all_tiers[tier] = all_tiers.get(tier, 0) + n
        pct = lambda v: f"{100 * v / rep.rows:.1f}%" if rep.rows else "-"
        table.add_row(
            rep.slug,
            str(rep.rows),
            f"{rep.current} [dim]{pct(rep.current)}[/]",
            f"{rep.proposed} [dim]{pct(rep.proposed)}[/]",
            f"[red]{len(rep.lost)}[/]" if rep.lost else "0",
            f"[green]{len(rep.gained)}[/]" if rep.gained else "0",
            f"[yellow]{len(rep.lexicon_gaps)}[/]" if rep.lexicon_gaps else "0",
        )

    if len(reports) > 1:
        pct = lambda v: f"{100 * v / totals['rows']:.1f}%" if totals["rows"] else "-"
        table.add_section()
        table.add_row(
            "[bold]total[/]",
            str(totals["rows"]),
            f"[bold]{totals['current']}[/] [dim]{pct(totals['current'])}[/]",
            f"[bold]{totals['proposed']}[/] [dim]{pct(totals['proposed'])}[/]",
            f"[bold]{totals['lost']}[/]",
            f"[bold]{totals['gained']}[/]",
            f"[bold]{len(all_gaps)}[/]",
        )
    print(table)

    # Rows are the wrong denominator on their own -- a row that acquires forty
    # spurious names still counts once. These are the precision numbers.
    pc, pp, pk = (totals[k] for k in ("pairs_current", "pairs_proposed", "pairs_kept"))
    cc, cp = totals["concepts_current"], totals["concepts_proposed"]
    if pc:
        print(
            f"matches: current [bold]{pc}[/] -> proposed [bold]{pp}[/]"
            f" ([bold]{pp / pc:.2f}x[/]), keeping {100 * pk / pc:.1f}% of current"
        )
        print(
            f"concepts: current [bold]{cc}[/] -> proposed [bold]{cp}[/]"
            f" ([bold]{cp / max(cc, 1):.2f}x[/])"
            "  [dim]-- the gap between these two is synonym expansion[/]"
        )

    if all_basis:
        from ..match.strat_names import LocationBasis

        order = [b.value for b in LocationBasis if b.value in all_basis]
        total = sum(all_basis.values())
        print(
            "location: "
            + "  ".join(
                f"{b}={all_basis[b]} [dim]{100 * all_basis[b] / total:.1f}%[/]"
                for b in order
            )
        )

    if all_tiers:
        order = [t for t in FIELD_TIERS if t in all_tiers]
        summary = "  ".join(f"{t}={all_tiers[t]}" for t in order)
        print(f"[dim]ids by strongest field:[/] {summary}")

    # Not a matching failure: a formally named unit -- the text gave it a rank --
    # that Macrostrat's lexicon does not carry. A large number here is a signal
    # that the source needs lexicon ingestion, not better matching.
    if all_gaps:
        print(
            f"\n[yellow]{len(all_gaps)}[/] rank-bearing names with no lexicon entry"
            " [dim](candidates for lexicon ingestion)[/]"
        )
        for name in sorted(all_gaps)[:examples]:
            print(f"  [yellow]gap[/] {name}")

    if examples_from:
        _print_field_examples(reports, examples_from, examples, full_text)
        return

    # Losses are the ones that matter: a match the current pipeline found and
    # this one did not is a regression, whatever the headline rate says.
    for rep in reports:
        if not rep.lost and not rep.gained:
            continue
        print(f"\n[bold]{rep.slug}[/]")
        for label, style, rows in (
            ("lost", "red", rep.lost),
            ("gained", "green", rep.gained),
        ):
            for ex in rows[:examples]:
                print(f"  [{style}]{label}[/] {ex.text[:72]!r}")
                for match_field, key, name, basis in ex.matches[:4]:
                    if key is None:
                        print(f"        -> {name}")
                    else:
                        print(
                            f"        [dim]{match_field}[/] {key!r}"
                            f" -> {name} [dim]({basis})[/]"
                        )
                if full_text:
                    _print_texts(ex)


def _highlight(text: str, keys) -> str:
    """Mark every word of every matched name, so it can be found by eye."""
    from rich.markup import escape

    words = {w for key in keys if key for w in key.split() if len(w) > 2}
    if not words:
        return escape(text)
    pattern = re.compile(
        r"\b("
        + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        + r")\b",
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: f"[bold yellow]{escape(m.group(0))}[/]", escape(text))


def _print_texts(ex):
    keys = [key for _, key, _, _ in ex.matches]
    for name, text in ex.texts.items():
        print(f"        [dim]{name}:[/] {_highlight(text, keys)}")


def _print_field_examples(reports, field, limit, full_text):
    """Worked examples of matches from one field, for reading rather than counting."""
    for rep in reports:
        found = rep.by_field_examples.get(field)
        if not found:
            continue
        print(f"\n[bold]{rep.slug}[/] -- matches from [cyan]{field}[/]")
        for ex in found[:limit]:
            print(f"\n  {ex.text[:76]!r}")
            for _, key, name, basis in ex.matches:
                print(f"        {key!r} -> [bold]{name}[/] [dim]({basis})[/]")
            if full_text:
                _print_texts(ex)


@cli.command(name="finalize", rich_help_panel="Map")
def finalize(maps: MapSelector):
    """Finalize the selected map sources."""
    for_each_map(maps, finalize_one)


def finalize_one(map: MapInfo):
    """
    Finalize a map source by setting is_finalized to True in the sources table.

    This is a computed parameter, so we can change its design in the future.
    """
    db = get_database()
    is_finalized = has_map_schema_data(db, map)

    if is_finalized:
        set_finalized(map)
        print(f"Map {map.id} {map.slug} is finalized")
    else:
        raise MacrostratError(
            f"Map {map.id} {map.slug} has no data in the [cyan]maps[/cyan] schema"
        )


def set_finalized(map: MapInfo):
    """
    Set a map source as finalized
    """
    db = get_database()
    db.run_query(
        "UPDATE maps.sources SET is_finalized = TRUE WHERE source_id = :map_id",
        dict(map_id=map.id),
    )
    db.session.commit()
