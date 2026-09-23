"""Score the legend-grain strat-name matcher against what the pipeline holds.

Read-only. Nothing here writes: it reports what `match_strat_names` *would* find
beside `maps.legend.strat_name_ids` as it stands, so the two can be compared
before a source is re-matched. Behind `macrostrat maps process strat-names-report`.
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from rich import print
from rich.markup import escape
from rich.table import Table

from macrostrat.core.exc import MacrostratError
from macrostrat.database import Database

from .strat_names import (
    DEFAULT_BUFFER,
    FIELD_TIERS,
    LocationBasis,
    RowMatch,
    _gaps,
    legend_rows,
    match_source,
    prepare,
)

#: How many worked examples to keep per field, for `--field`.
EXAMPLES_PER_FIELD = 40


@dataclass
class Example:
    """One legend entry, with every match shown as text rather than an id."""

    #: The map's own words.
    text: str
    #: `(field, cleaned name that matched, lexicon name, location basis)`. The
    #: first, second and fourth are None for a match the current pipeline made,
    #: which records none of them.
    matches: list
    #: The source text of each field that produced a match, whole. A match out of
    #: a description cannot be judged from the name alone -- "Correlative with
    #: ... the Hawley Formation" and "is the Hawley Formation" read identically
    #: once the sentence is gone.
    texts: dict = field(default_factory=dict)


@dataclass
class SourceReport:
    slug: str
    rows: int = 0
    current: int = 0
    proposed: int = 0
    both: int = 0
    shared: int = 0
    superset: int = 0
    #: How many rows each tier was the strongest evidence for.
    by_tier: dict = field(default_factory=dict)
    #: Distinct rank-bearing names this source uses that the lexicon lacks.
    lexicon_gaps: set = field(default_factory=set)
    #: How many matches each `LocationBasis` accounts for.
    by_basis: dict = field(default_factory=dict)
    #: A few worked examples per `match_field`, for reading rather than counting.
    by_field_examples: dict = field(default_factory=dict)
    lost: list = field(default_factory=list)
    gained: list = field(default_factory=list)
    #: Matches, not rows. A row counts once however many names it acquires, so
    #: row totals cannot see over-matching at all -- they read 71% against 74%
    #: while the prototype was emitting five times as many matches as the
    #: pipeline it was being scored against. Precision lives here.
    pairs_current: int = 0
    pairs_proposed: int = 0
    pairs_kept: int = 0
    concepts_current: int = 0
    concepts_proposed: int = 0


def report_for_source(
    db: Database,
    slug: str,
    lexicon,
    buffer: float = DEFAULT_BUFFER,
    fields=FIELD_TIERS,
) -> SourceReport:
    rep = SourceReport(slug)
    rows = legend_rows(db, slug)
    concepts = dict(
        db.run_query(
            "SELECT strat_name_id, concept_id FROM macrostrat.lookup_strat_names"
            " WHERE concept_id IS NOT NULL"
        ).all()
    )
    found = match_source(db, slug, lexicon, buffer=buffer, fields=fields)
    survives = {(m.legend_id, m.strat_name_id) for m in found}
    names = dict(
        db.run_query(
            "SELECT strat_name_id, rank_name FROM macrostrat.lookup_strat_names"
        ).all()
    )
    basis = {(m.legend_id, m.strat_name_id): m.location_basis.value for m in found}
    # `match_source` already matched the text; re-deriving it here would double
    # the work. Rebuild the per-row view from what it returned.
    matched = {r.legend_id: RowMatch() for r in rows}
    for m in found:
        matched[m.legend_id].by_id[m.strat_name_id] = m.match_field
        matched[m.legend_id].keys[m.strat_name_id] = m.matched_text
    for r in rows:
        matched[r.legend_id].lexicon_gaps = _gaps(r, lexicon)
    rep.by_basis = Counter(m.location_basis.value for m in found)

    cur_pairs = {(r.legend_id, i) for r in rows for i in (r.strat_name_ids or [])}
    rep.pairs_current = len(cur_pairs)
    rep.pairs_proposed = len(survives)
    rep.pairs_kept = len(cur_pairs & survives)
    rep.concepts_current = len(
        {(l, concepts[i]) for l, i in cur_pairs if i in concepts}
    )
    rep.concepts_proposed = len(
        {(l, concepts[i]) for l, i in survives if i in concepts}
    )

    for r in rows:
        rep.rows += 1
        current = set(r.strat_name_ids or [])
        m = matched[r.legend_id]
        m.by_id = {i: t for i, t in m.by_id.items() if (r.legend_id, i) in survives}
        proposed = set(m.by_id)
        rep.lexicon_gaps |= m.lexicon_gaps
        for tier in m.by_id.values():
            rep.by_tier[tier] = rep.by_tier.get(tier, 0) + 1
        if current:
            rep.current += 1
        if proposed:
            rep.proposed += 1
        if current and proposed:
            rep.both += 1
            if current & proposed:
                rep.shared += 1
            if current <= proposed:
                rep.superset += 1
        elif current:
            rep.lost.append(
                Example(
                    text=r.strat_name or r.name or "",
                    matches=[
                        (None, None, names.get(i, str(i)), None)
                        for i in sorted(current)
                    ],
                )
            )
        # Examples per field, independent of whether the row is a gain -- a
        # correlative mention usually lands on a row that already matched.
        for f in set(m.by_id.values()):
            bucket = rep.by_field_examples.setdefault(f, [])
            if len(bucket) < EXAMPLES_PER_FIELD:
                bucket.append(
                    Example(
                        text=r.strat_name or r.name or "",
                        matches=[
                            (
                                m.by_id[i],
                                m.keys.get(i),
                                names.get(i, str(i)),
                                basis.get((r.legend_id, i)),
                            )
                            for i in sorted(proposed)
                            if m.by_id[i] == f
                        ],
                        texts={
                            t: getattr(r, t)
                            for t in FIELD_TIERS
                            if getattr(r, t, None) and t in set(m.by_id.values())
                        },
                    )
                )
        if proposed and not current:
            rep.gained.append(
                Example(
                    text=r.strat_name or r.name or "",
                    matches=[
                        (
                            m.by_id[i],
                            m.keys.get(i),
                            names.get(i, str(i)),
                            basis.get((r.legend_id, i)),
                        )
                        for i in sorted(proposed)
                    ],
                )
            )
    return rep


def sources_matching(db: Database, pattern: str) -> list[str]:
    return list(
        db.run_query(
            """
            SELECT DISTINCT s.slug FROM maps.sources s
            JOIN maps.legend lg ON lg.source_id = s.source_id
            WHERE s.slug LIKE :pattern
            ORDER BY 1
            """,
            dict(pattern=pattern),
        ).scalars()
    )


def strat_names_report(
    db: Database,
    pattern: str,
    *,
    fields=FIELD_TIERS,
    examples: int = 4,
    examples_from: str | None = None,
    full_text: bool = False,
):
    """Print the prototype-vs-current comparison for every source matching `pattern`.

    SGMC is the benchmark: clean legend text, 96.7% matched by the current
    twelve-pass pipeline. Reaching that is the bar for adopting this on NGS.
    """
    print("[dim]Normalizing the lexicon[/]")
    lexicon = prepare(db)

    slugs = sources_matching(db, pattern)
    if not slugs:
        raise MacrostratError(f"No sources with legend rows match {pattern}")

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
        rep = report_for_source(db, slug, lexicon, fields=fields)
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
