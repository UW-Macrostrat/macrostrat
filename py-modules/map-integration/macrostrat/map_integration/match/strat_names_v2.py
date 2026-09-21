"""Prototype: match map legend names to the lexicon, at legend grain.

An alternative to `match/strat_names.py`, which runs twelve additive SQL passes
per source and writes ~9 copies of every fact it finds. This does the comparison
in Python over a blocked candidate set, once per legend entry, and reports
instead of writing.

Read-only on purpose. It exists to be measured against what the current pipeline
produced, and the benchmark is SGMC, whose legend text is clean and which the
current pipeline matches at 96.7%. See [[Map geologic name matching]].

Three things differ from the SQL pipeline, and each was forced by a measurement:

1. **Both sides are normalized by the same function.** `clean_strat_name` runs
   over the map text and over the lexicon, rather than comparing map text
   cleaned one way against `name_no_lith` computed another.

2. **Rank does not veto.** `macrostrat.strat_names.rank` has no `Suite`, so
   "New Hampshire Plutonic Suite" is stored as `Gp` while its own name says
   Suite; and a map may legitimately call a Macrostrat group a formation
   ("Chilhowee"). Vetoing on rank cost 110 true matches on SGMC. It is recorded
   as evidence instead.

3. **The lexicon is indexed under both its bare name and `rank_name`.**
   Normalizing the bare form alone is lossy exactly where it matters: `Wagon Bed`
   cleans to `wagon`, because with no trailing "Formation" the `Bed` reads as the
   rank. `rank_name` holds `Wagon Bed Formation`, which is how a map writes it.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from macrostrat.database import Database
from macrostrat.match_utils.strat_names import (
    StratRank,
    clean_strat_name,
    create_ignore_list,
)

_RANK_BY_VALUE = {r.value: r for r in StratRank}


@dataclass
class Candidate:
    strat_name_id: int
    #: Every rank asserted for this name, from the `rank` column and from the
    #: name's own text. They disagree often enough that both are kept.
    ranks: set = field(default_factory=set)


def build_lexicon(db: Database) -> dict[str, list[Candidate]]:
    """Normalize the whole lexicon once. 51k entries, so this is cheap."""
    lexicon: dict[str, list[Candidate]] = defaultdict(list)
    rows = db.run_query(
        "SELECT strat_name_id, strat_name, rank_name, rank"
        " FROM macrostrat.lookup_strat_names"
    )
    for r in rows:
        rank_db = _RANK_BY_VALUE.get((r.rank or "").lower())
        for text in {r.strat_name, r.rank_name} - {None}:
            try:
                parsed = clean_strat_name(text, split_hierarchy=False)
            except Exception:
                continue
            for p in parsed:
                lexicon[p.name].append(
                    Candidate(r.strat_name_id, {rank_db, p.rank} - {None})
                )
    return lexicon


def allowed_names(db: Database, slug: str) -> set[int]:
    """Names this source could plausibly use: spatially near it, or unplaced.

    The spatial half is the blocking `matched-strat-names.sql` already does and
    does quickly. The unplaced half matters because 2,693 of 51,229 lexicon
    entries have no footprint at all, and a name cannot be excluded on geography
    that was never recorded.
    """
    near = set(
        db.run_query(
            """
            SELECT snf.strat_name_id
            FROM macrostrat.strat_name_footprints snf
            JOIN maps.sources s ON ST_Intersects(snf.geom, s.rgeom)
            WHERE s.slug = :slug
            """,
            dict(slug=slug),
        ).scalars()
    )
    unplaced = set(
        db.run_query(
            """
            SELECT lsn.strat_name_id FROM macrostrat.lookup_strat_names lsn
            WHERE NOT EXISTS (
              SELECT 1 FROM macrostrat.strat_name_footprints f
              WHERE f.strat_name_id = lsn.strat_name_id
            )
            """
        ).scalars()
    )
    return near | unplaced


#: The legend's text fields, strongest evidence first.
#:
#: Field of origin is evidence, not preprocessing. A name in `strat_name` or
#: `name` *is* this unit; a name in `descrip` is a *mention*, which may be the
#: unit or may be a correlative or bounding one ("overlies the X Formation").
#: Collapsing that distinction is what `extract-strat-names` did -- it
#: concatenated every column, matched once at ingest, and wrote the result back
#: into `strat_name`, discarding any unit where more than three names hit. That
#: froze the answer against later description edits and threw away exactly the
#: units a rich description names. Here the fields stay separate and the tier
#: rides along with the match.
FIELD_TIERS = ("strat_name", "name", "descrip", "comments")


@dataclass
class RowMatch:
    #: strat_name_id -> the strongest field it was found in.
    by_id: dict = field(default_factory=dict)
    #: Names that parsed with a rank -- so the text structurally declared a
    #: stratigraphic unit -- and matched nothing in the lexicon. Not a failure of
    #: matching: a formally named unit Macrostrat's lexicon does not carry.
    lexicon_gaps: set = field(default_factory=set)

    def __bool__(self):
        return bool(self.by_id)


def match_text(text: str, lexicon, allowed: set[int]) -> list[tuple[int, bool]]:
    """`(strat_name_id, rank_agrees)` for every lexicon entry this text names."""
    out = []
    for p, cand in _candidates(text, lexicon, allowed):
        agrees = not p.rank or not cand.ranks or p.rank in cand.ranks
        out.append((cand.strat_name_id, agrees))
    return out


def _candidates(text: str, lexicon, allowed: set[int]):
    for p in _parse(text):
        for cand in lexicon.get(p.name, ()):
            if cand.strat_name_id in allowed:
                yield p, cand


def _parse(text: str):
    try:
        return clean_strat_name(text, split_hierarchy=True)
    except Exception:
        return []


def match_row(row, lexicon, allowed: set[int], fields=FIELD_TIERS) -> RowMatch:
    """Match every text field, keeping the strongest field each id came from."""
    result = RowMatch()
    for tier in fields:
        text = getattr(row, tier, None)
        if not text:
            continue
        for p, cand in _candidates(text, lexicon, allowed):
            result.by_id.setdefault(cand.strat_name_id, tier)
    # Gaps are judged on the authoritative fields only. A rank-bearing name in a
    # description is as likely to be a unit from a neighbouring column as one
    # this map failed to link.
    for tier in ("strat_name", "name"):
        text = getattr(row, tier, None)
        if not text:
            continue
        for p in _parse(text):
            if p.rank is not None and p.name not in lexicon:
                result.lexicon_gaps.add(p.name)
    return result


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
    lost: list = field(default_factory=list)
    gained: list = field(default_factory=list)


def report_for_source(db: Database, slug: str, lexicon) -> SourceReport:
    rep = SourceReport(slug)
    allowed = allowed_names(db, slug)
    rows = db.run_query(
        """
        SELECT lg.legend_id, lg.name, lg.strat_name, lg.descrip, lg.comments,
               lg.strat_name_ids
        FROM maps.legend lg JOIN maps.sources s ON s.source_id = lg.source_id
        WHERE s.slug = :slug
        """,
        dict(slug=slug),
    ).all()
    for r in rows:
        rep.rows += 1
        current = set(r.strat_name_ids or [])
        m = match_row(r, lexicon, allowed)
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
            rep.lost.append((r.strat_name or r.name, sorted(current)))
        elif proposed:
            rep.gained.append((r.strat_name or r.name, sorted(proposed)))
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


def prepare(db: Database):
    """Load the lithology vocabulary the normalizer needs, then the lexicon."""
    create_ignore_list(
        db.run_query("SELECT lith FROM macrostrat.liths").scalars().all()
    )
    return build_lexicon(db)
