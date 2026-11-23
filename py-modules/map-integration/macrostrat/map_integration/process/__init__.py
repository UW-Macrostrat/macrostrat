"""
Map processing pipeline (v2)

+ macrostrat maps process insert <source_id>
+ macrostrat maps process bounds <source_id>
+ macrostrat process legend <source_id>
+ macrostrat match strat_names <source_id>
+ macrostrat match units <source_id>
+ macrostrat match liths <source_id>
+ macrostrat process burwell_lookup <source_id>
+ macrostrat process legend_lookup <source_id>
+ macrostrat process carto <source_id>
+ macrostrat process carto_lines <source_id>
+ macrostrat seed <source_id>

+ macrostrat maps process dedupe <source_id>  (repair: a map staged twice)

"""

from functools import partial
from pathlib import Path
from typing import Annotated, Optional

from rich import print
from typer import Argument, Exit, Option

from macrostrat.app_frame.environments import AccessScope
from macrostrat.core.exc import MacrostratError
from macrostrat.core.safety import require_write_access

from ..database import get_database, sql_file
from ..match import match_liths, match_strat_names, match_units
from ..match.utils import SourceNotMaterialized
from ..utils import IngestionCLI
from ..utils.map_info import (
    MapExclude,
    MapInfo,
    MapSelector,
    MapSince,
    MapState,
    MapUnfinalized,
    has_map_schema_data,
    resolve_maps,
)
from .geometry import create_bounds
from .insert import copy_to_maps, remove
from .legend_lookup import legend_lookup
from .lookup import make_lookup
from .status import processing_status

cli = IngestionCLI(
    no_args_is_help=True, name="process", help="Process map data once ingested"
)

pipeline_steps_panel = "[dim]Pipeline steps[/]"


_REQUIREMENTS = {
    "polygons": """
        SELECT DISTINCT source_id FROM maps.polygons
        WHERE source_id = ANY(CAST(:ids AS integer[]))
    """,
}


def for_each_map(
    selectors, step, exclude=None, state=None, since=None, unfinalized=False, **kwargs
):
    """Run a single-map processing step over every selected map.

    Every step in this module takes a `MapInfo` first and options after, so one
    adapter covers all of them. Failures are collected rather than aborting the
    sweep: over 114 maps, stopping on the first bad one wastes the rest of the
    run, and the summary says which to look at.
    """
    db = get_database()
    maps = resolve_maps(
        db, selectors, exclude=exclude, state=state, since=since, unfinalized=unfinalized
    )
    many = len(maps) > 1
    if many:
        print(f"[dim]{len(maps)} maps[/]")

    # What a step needs before it has anything to do: its own polygons (the
    # default), its bounds, or nothing. A source without it is skipped, not
    # failed -- compilations and mosaic members hold no polygons, and a
    # registered but uncopied source has none yet.
    requires = kwargs.pop("requires", "polygons")
    ready = {m.id for m in maps}
    if requires is not None:
        ready = set(
            db.run_query(
                _REQUIREMENTS[requires], {"ids": [m.id for m in maps]}
            ).scalars()
        )

    failed = []
    skipped = []
    for m in maps:
        if m.id not in ready:
            skipped.append(m.slug)
            if many:
                print(f"[dim]{m.slug} #{m.id} -- no {requires}, skipped[/]")
            elif requires == "polygons":
                raise SourceNotMaterialized(
                    f"Source {m.id} ({m.slug}) has no polygons in any scale table"
                )
            else:
                raise MacrostratError(f"Source {m.id} ({m.slug}) has no {requires}")
            continue
        if many:
            print(f"[bold cyan]{m.slug}[/] [dim]#{m.id}[/]")
        try:
            step(m, **kwargs)
        except Exception as err:  # noqa: BLE001 -- reported per map, see above
            if not many:
                raise
            failed.append((m.slug, str(err).strip().splitlines()[0]))
            print(f"  [red]failed[/] {failed[-1][1]}")

    if skipped:
        print(f"\n[dim]{len(skipped)} of {len(maps)} skipped (no {requires})[/]")
    if failed:
        print(f"\n[red]{len(failed)} of {len(maps)} failed[/]")
        for slug, err in failed:
            print(f"  [red]{slug}[/] {err}")
        raise MacrostratError(f"{len(failed)} maps failed")


def run_pipeline(
    source: MapInfo,
    delete_existing: bool = False,
    scale: str = None,
    allow_unattributed: bool = False,
):
    """Run the full post-ingestion pipeline for one map source."""
    db = get_database()
    try:
        copy_to_maps(
            db,
            source,
            delete_existing=delete_existing,
            scale=scale,
            allow_unattributed=allow_unattributed,
        )
    except ValueError as e:
        print(e)
        if not delete_existing:
            print("Continuing with existing map data")
    create_bounds(db, source)
    run_legend(source)
    match_strat_names(db, source)
    match_units(db, source)
    match_liths(db, source)
    make_lookup(db, source)
    legend_lookup(db, source)
    finalize_one(source)


def run_legend(map: MapInfo):
    """Update legend lookup tables for one map source."""
    db = get_database()
    proc = sql_file("update-legend")
    db.run_sql(proc, {"source_id": map.id})


@cli.command(name="preflight", rich_help_panel="Process")
def preflight_command(
    maps: MapSelector,
    exclude: MapExclude = None,
    state: MapState = None,
    since: MapSince = None,
    unfinalized: MapUnfinalized = False,
    out: Annotated[
        Optional[Path],
        Option("--out", help="Also write every finding to this CSV."),
    ] = None,
):
    """
    Report what `insert` would refuse in each selected map's staged tables, and
    the layers none of whose features has any details. Reads only; exits 1 if
    any map would fail to insert. Run before `pipeline`.

        macrostrat maps process preflight 'arizona-*' --since 2026-11-17

    Blocks insert: no scale, no polygons, a missing copied column or one of a
    type maps refuses, geometry maps refuses (pipeline --fix-geometries),
    strike, dip or dip_dir out of range (normalize review-points), text longer
    than its maps column, and lith/t_interval/b_interval null on every polygon
    (pipeline --allow-unattributed).

    No details: a polygons, lines or points table none of whose features has a
    name, description, type, lithology (or strike and dip). Every column it does
    have is listed per source layer, with examples, to decide the legend merge
    or column mapping it needs in data-integration.
    """
    import csv

    from rich.markup import escape

    from ..commands.preflight import Finding, maps_limits, preflight

    db = get_database()
    selected = resolve_maps(
        db, maps, exclude=exclude, state=state, since=since, unfinalized=unfinalized
    )
    scales = dict(
        db.run_query(
            "SELECT source_id, scale FROM maps.sources WHERE source_id = ANY(:ids)",
            dict(ids=[m.id for m in selected]),
        ).all()
    )
    limits = maps_limits(db)
    everything: list[Finding] = []
    blocked: dict[str, list[str]] = {}
    no_details: list[tuple[str, str, int]] = []
    for position, m in enumerate(selected, start=1):
        print(f"\n[bold cyan]({position}/{len(selected)}) {m.slug}[/bold cyan]")
        try:
            findings, counts, details = preflight(
                db, m.slug, m.id, scales.get(m.id), limits
            )
        except Exception as e:  # noqa: BLE001 -- reported per map
            db.session.rollback()
            print(f"  [red]Failed:[/red] {escape(str(e))}")
            blocked[m.slug] = [f"preflight failed: {e}"]
            continue
        print(
            "  "
            + "   ".join(
                f"{kind} {n:,}"
                + (f" ([yellow]{bare:,} undescribed[/yellow])" if bare else "")
                for kind, (n, bare) in counts.items()
            )
        )
        for f in findings:
            mark = "[red]blocks insert[/red]" if f.blocks else "[yellow]warning[/yellow]"
            count = f" {f.count:,}" if f.count else ""
            print(f"  {mark} {f.table} {f.check}{count} [dim]{escape(f.detail)}[/dim]")
        if blocks := [
            f"{f.table}: {f.check}" if f.table else f.check
            for f in findings
            if f.blocks
        ]:
            blocked[m.slug] = blocks
        for kind, (n, bare) in counts.items():
            if not n or bare != n:
                continue
            no_details.append((m.slug, kind, n))
            everything.append(Finding(m.slug, kind, "no feature has details", n))
            print(
                f"  [yellow]no details[/yellow] {kind}: none of {n:,} features"
                " says what it is. Its columns:"
            )
            layer = None
            for d in (d for d in details if d.table == kind):
                if d.source_layer != layer:
                    layer = d.source_layer
                    print(f"    [bold]{escape(layer or '(no source_layer)')}[/bold]")
                print(
                    f"      {d.check.removeprefix('column '):<28} {d.count:>7,}"
                    f"  [dim]{escape(d.detail)}[/dim]"
                )
        everything += findings + details

    print(f"\n[bold]{len(selected)} map(s)[/bold]")
    if blocked:
        print(f"[red]{len(blocked)} would fail to insert:[/red]")
        for slug, blocks in blocked.items():
            print(f"  {slug}: {escape('; '.join(blocks))}")
    else:
        print("[green]None would fail to insert.[/green]")
    if no_details:
        print(f"[yellow]{len(no_details)} layer(s) with no details:[/yellow]")
        for slug, kind, n in no_details:
            print(f"  {slug} {kind} ({n:,} features)")
    if out is not None:
        with Path(out).open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["slug", "table", "source_layer", "check", "count", "detail", "blocks_insert"]
            )
            for x in everything:
                writer.writerow(
                    [x.slug, x.table, x.source_layer, x.check, x.count, x.detail, x.blocks]
                )
        print(f"{len(everything):,} row(s) -> {out}")
    if blocked:
        raise Exit(1)


@cli.command(name="pipeline", rich_help_panel="Process")
def pipeline(
    maps: MapSelector,
    delete_existing: bool = False,
    scale: str = None,
    exclude: MapExclude = None,
    state: MapState = None,
    since: MapSince = None,
    unfinalized: MapUnfinalized = False,
    fix_geometries: Annotated[
        bool,
        Option(
            "--fix-geometries",
            help="Repair each map's invalid staged geometries first"
            " (macrostrat maps fix-geometries)",
        ),
    ] = False,
    allow_unattributed: Annotated[
        bool,
        Option(
            "--allow-unattributed",
            help="Insert even though lith/t_interval/b_interval are entirely null",
        ),
    ] = False,
):
    """
    Run the full post-pipeline for the selected map sources

    This includes:
    - Copy to maps schema
    - Boundary from the map's polygons
    - Legend lookup table generation
    - Match strat names
    - Match units
    - Match liths
    - Make lookup
    - Finalize

    A bulk ingest's maps, picking up after a run that failed partway:

        macrostrat maps process pipeline 'arizona-*' --exclude 'arizona-adgm-*' \\
            --since 2026-11-17 --state ready --unfinalized --fix-geometries \\
            --delete-existing

    --delete-existing replaces what a failed run left in the maps schema.
    """

    def step(source: MapInfo, **kwargs):
        if fix_geometries:
            from ..commands.fix_geometries import fix_geometries as repair

            repair(get_database(), source)
        run_pipeline(source, **kwargs)

    for_each_map(
        maps,
        step,
        exclude=exclude,
        state=state,
        since=since,
        unfinalized=unfinalized,
        delete_existing=delete_existing,
        scale=scale,
        allow_unattributed=allow_unattributed,
        # Its first step is the insert, so a map without polygons yet is the usual case.
        requires=None,
    )


@cli.command(name="insert", rich_help_panel=pipeline_steps_panel)
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
    exclude: MapExclude = None,
    state: MapState = None,
):
    """Copy staged data to the maps schema.

    A compilation whose members share one staging table passes it once:
    `insert 'ngs-*' --staging-prefix ngs` covers all 114.
    """
    for_each_map(
        maps,
        partial(copy_to_maps, get_database()),
        exclude=exclude,
        state=state,
        delete_existing=delete_existing,
        scale=scale,
        staging_prefix=staging_prefix,
        allow_unattributed=allow_unattributed,
        requires=None,
    )


@cli.command(name="bounds", rich_help_panel=pipeline_steps_panel)
def bounds(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Set each map's boundary to the union of its polygons.

    Matching reads the boundary. Before the insert it comes from the staging
    table. A boundary composed from operations belongs to `macrostrat bounds build`.
    """
    for_each_map(
        maps,
        partial(create_bounds, get_database()),
        exclude=exclude,
        state=state,
        requires=None,
    )


@cli.command(name="legend", rich_help_panel=pipeline_steps_panel)
def legend(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Update legend lookup tables and colors."""
    try:
        for_each_map(maps, run_legend, exclude=exclude, state=state)
    finally:
        # Stale estimates flip the strat-name footprint query into a full spatial join.
        get_database().run_sql("ANALYZE maps.legend, maps.map_legend")


@cli.command(name="strat-names", rich_help_panel=pipeline_steps_panel)
def strat_names(
    maps: MapSelector,
    field: str = Option(None, help="Match only on this legend field (e.g. descrip)"),
    exclude: MapExclude = None,
    state: MapState = None,
):
    """Match stratigraphic names."""
    db = get_database()
    for_each_map(
        maps,
        partial(match_strat_names, db, fields=_match_fields(field)),
        exclude=exclude,
        state=state,
    )


@cli.command(name="units", rich_help_panel=pipeline_steps_panel)
def units(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Match column units."""
    db = get_database()
    for_each_map(maps, partial(match_units, db), exclude=exclude, state=state)


@cli.command(name="liths", rich_help_panel=pipeline_steps_panel)
def liths(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Match lithologies."""
    db = get_database()
    for_each_map(maps, partial(match_liths, db), exclude=exclude, state=state)


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


@cli.command(name="lookup", rich_help_panel=pipeline_steps_panel)
def lookup(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Refresh the lookup tables for the selected map sources."""
    db = get_database()
    for_each_map(maps, partial(lookup_combined, db), exclude=exclude, state=state)


def lookup_combined(db, source: MapInfo):
    """Refresh the lookup tables for one map source."""
    # Note: merges the v1 lookup and legend-lookup commands
    make_lookup(db, source)
    legend_lookup(db, source)


@cli.command(name="finalize", rich_help_panel=pipeline_steps_panel)
def finalize(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Finalize the selected map sources."""
    for_each_map(maps, finalize_one, exclude=exclude, state=state)


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


@cli.command(name="names-report", rich_help_panel="Utils")
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
    """Score the strat-names matcher against what the current pipeline produced.

    Read-only; reports what a
    legend-grain matcher *would* find relative to the current matches
    """
    from ..match.strat_names_report import strat_names_report as report

    report(
        get_database(),
        pattern,
        fields=_match_fields(field),
        examples=examples,
        examples_from=examples_from,
        full_text=full_text,
    )


cli.add_command(processing_status, name="status", rich_help_panel="Utils")


@cli.command(name="remove", rich_help_panel="[red]Destructive[/red]")
def delete(maps: MapSelector, exclude: MapExclude = None, state: MapState = None):
    """Delete all data from the maps schema for the selected map sources."""
    db = get_database()
    for_each_map(maps, partial(remove, db), exclude=exclude, state=state)


@cli.command(name="dedupe", rich_help_panel="[red]Destructive[/red]")
def dedupe(
    maps: MapSelector,
    exclude: MapExclude = None,
    state: MapState = None,
    staging_prefix: Annotated[
        Optional[str],
        Option(
            "--staging-prefix",
            help="Name the sources.<prefix>_* staging tables (default: the slug)",
        ),
    ] = None,
    dry_run: bool = Option(False, "--dry-run", help="Report duplicates only"),
    yes: bool = Option(
        False, "--yes", "-y", help="Skip the confirmation prompt where one is allowed"
    ),
):
    """Delete features that exactly duplicate another of the same map.

    Covers the published and staging tables. Rows must match in every column but
    their key; the first of each set is kept.
    """
    from .dedupe import count_duplicates, remove_duplicates

    db = get_database()
    found = []
    for m in resolve_maps(db, maps, exclude=exclude, state=state):
        counts = count_duplicates(db, m, staging_prefix=staging_prefix)
        print(f"[bold cyan]{m.slug}[/] [dim]#{m.id}[/]")
        for c in counts:
            style = "yellow" if c.duplicates else "dim"
            print(
                f"  [{style}]{c.table:<48} {c.rows:>9} rows"
                f" {c.duplicates:>9} duplicates[/]"
            )
        if any(c.duplicates for c in counts):
            found.append((m, sum(c.duplicates for c in counts)))

    total = sum(n for _, n in found)
    if total == 0:
        print("\nNo duplicates found")
        return
    if dry_run:
        print(f"\nDry run; {total} duplicate rows in {len(found)} maps not deleted")
        return

    require_write_access(
        AccessScope.Data,
        assume_yes=yes,
        action=f"deletion of {total} duplicate rows from {len(found)} map(s)",
    )
    # The gate replaces the reader connection with a writer one
    db = get_database()
    for m, _ in found:
        deleted = remove_duplicates(db, m, staging_prefix=staging_prefix)
        summary = ", ".join(f"{t} {n}" for t, n in deleted.items() if n)
        print(f"{m.slug}: deleted {summary}")
