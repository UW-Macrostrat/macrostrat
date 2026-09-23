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

4. **Prose has to earn its matches.** `descrip` is read; `comments` is not, and
   `FIELD_TIERS` says why. A phrase in a description is accepted only if it
   names a unit rather than describing a rock -- see `_names_a_unit`. Without
   that test prose produced three times as many matches as the whole SQL
   pipeline, almost all of them collisions between a stripped description and a
   lexicon entry whose name is an ordinary word.

5. **Geography falls back to the reference, not to nothing.** A name with no
   footprint is placed by the paper that contributed it -- see `unplaced_allowed`.

The first version of this scored itself on *legend rows matched*, which is the
wrong denominator: it cannot see a row acquiring forty spurious names. Precision
is counted in pairs and in concepts.
"""

import time
from collections import Counter, defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum

from psycopg.sql import Identifier
from rich import print

from macrostrat.database import Database
from macrostrat.match_utils.strat_names import (
    StratRank,
    clean_strat_name,
    create_ignore_list,
)

from ..utils import MapInfo
from .utils import find_scale_table

_RANK_BY_VALUE = {r.value: r for r in StratRank}

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
#:
#: **`comments` is not read.** It is a provenance field, not a description of the
#: unit: 6,664 of SGMC's 6,727 populated comments are a citation beginning
#: "Original map source:", and the names matched out of one are the authors'
#: surnames. `Gale`, `Thompson`, `Walsh` and `Stanley` each claimed ~485 legend
#: entries from a single Vermont citation before this was noticed. Across SGMC
#: the field contributed 1,448 matches and *none* that the SQL pipeline also
#: found. Description is the floor for general text matching.
FIELD_TIERS = ("strat_name", "name", "descrip")

#: How many worked examples to keep per field, for `--field`.
EXAMPLES_PER_FIELD = 40

#: The fields that assert a unit's identity. The rest are prose.
NAME_FIELDS = frozenset({"strat_name", "name"})


@dataclass
class Candidate:
    strat_name_id: int
    #: Every rank asserted for this name, from the `rank` column and from the
    #: name's own text. They disagree often enough that both are kept.
    ranks: set = field(default_factory=set)
    #: The lithology words the cleaner stripped off this entry's own name --
    #: `granodiorite` for `Ravenswood Granodiorite`. Used to recognize the same
    #: unit named in free text, where there is no rank word to go on.
    liths: frozenset = frozenset()


def match_strat_names(db: Database, map_info: MapInfo, fields=FIELD_TIERS) -> int:
    slug = map_info.slug
    start = time.time()
    scope = "" if fields == FIELD_TIERS else f" [dim](from {', '.join(fields)})[/]"
    print(f"      Matching strat names for [bold cyan]{slug}[/]{scope}")

    lexicon = prepare(db)
    matches = match_source(db, slug, lexicon, fields=fields)
    inserted, updated, removed = write_matches(db, slug, matches)

    by_basis = {}
    for m in matches:
        by_basis[m.location_basis] = by_basis.get(m.location_basis, 0) + 1
    summary = "  ".join(
        f"{basis.value}={by_basis[basis]}"
        for basis in LocationBasis
        if basis in by_basis
    )
    unchanged = len(matches) - inserted - updated
    print(
        f"        Matched [bold cyan]{len(matches)}[/] strat names"
        f" in {time.time() - start:.1f}s"
        f" ([green]+{inserted}[/] ~{updated} [red]-{removed}[/],"
        f" {unchanged} unchanged)"
    )
    if summary:
        print(f"        {summary}")
    return len(matches)


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
                    Candidate(
                        r.strat_name_id,
                        {rank_db, p.rank} - {None},
                        frozenset(p.lith_signifiers),
                    )
                )
    return lexicon


#: Every word Macrostrat uses to describe a rock rather than name one --
#: lithologies, lithology attributes (colour, grain, bedform) and minerals,
#: 6,677 tokens in all. Loaded by `prepare`.
_descriptors: ContextVar[frozenset] = ContextVar("_descriptors", default=frozenset())


def describes_rock(name: str) -> bool:
    """Is this phrase made entirely of words for describing rock?

    `albite`, `biotite feldspathic`, `calcareous sandy` -- these are descriptions
    that survived cleaning because the cleaner strips lithologies but not the
    minerals and textures around them.

    Used only to decide what is worth reporting as a lexicon gap, and
    deliberately not as a veto on matching. Applied to matches it is
    net-negative: it removes 29 pairs from SGMC, but 13 of those are matches the
    SQL pipeline also found -- `Galena Formation`, `Muddy Sandstone`, `Mercury
    Limestone` -- real units whose proper noun happens to be a mineral or a
    texture. Applied to prose alone it removes nothing at all, because
    `_names_a_unit` has already excluded everything it would catch.
    """
    desc = _descriptors.get()
    return bool(name) and all(token in desc for token in name.split())


def unplaced_allowed(db: Database, slug: str) -> set[int]:
    """Footprintless names this source is allowed to use.

    5,830 lexicon entries have no footprint, so no spatial test can reach them.
    Admitting all of them -- on the reasoning that geography never recorded
    cannot exclude -- made the whole GNS New Zealand lexicon, 5,119 of that
    5,830, a candidate for every map in North America.

    Their *reference* is placed even where they are not, so that is what decides:
    a name is admitted if the paper that contributed it covers this source (247
    of them for SGMC), or if the reference has no geometry either (425), since
    then nothing has been said about where it is.
    """
    return set(
        db.run_query(
            """
            SELECT lsn.strat_name_id
            FROM macrostrat.lookup_strat_names lsn
            JOIN macrostrat.strat_names sn ON sn.id = lsn.strat_name_id
            LEFT JOIN macrostrat.refs rf ON rf.id = sn.ref_id
            WHERE NOT EXISTS (
              SELECT 1 FROM macrostrat.strat_name_footprints f
              WHERE f.strat_name_id = lsn.strat_name_id
            )
            AND (
              rf.rgeom IS NULL
              OR EXISTS (
                SELECT 1 FROM maps.sources s
                WHERE s.slug = :slug AND ST_Intersects(rf.rgeom, s.rgeom)
              )
            )
            """,
            dict(slug=slug),
        ).scalars()
    )


#: Degrees of slack between a footprint and a legend entry's envelope.
#:
#: Not a fudge factor for bad matches -- it is the resolution of the footprints,
#: which are built from column locations rather than from mapped extents and so
#: stop short of where a unit actually crops out. At 0 the test drops 58 of
#: SGMC's existing matches, among them `Metchosin Formation`, `Yakima Basalt` and
#: `Roslyn Formation`, all of them correct and all of them just outside their own
#: envelope. 0.25 degrees recovers 36 of those for 211 extra pairs; 1.2 -- what
#: the SQL pipeline's fuzzy-space pass used -- recovers only 6 more for another
#: 279, so the curve has flattened well before it.
DEFAULT_BUFFER = 0.25

#: Kilometres out to which a column counts as adjacent, as
#: `column-strat-names.sql` measures it: true distance on geography, so the reach
#: does not narrow east-west with latitude.
DEFAULT_COLUMN_TOLERANCE_KM = 25.0


class LocationBasis(str, Enum):
    """How the ground corroborates a name match, strongest first.

    The progression `macrostrat.match-utils` uses for SGP, translated from a
    point to a legend entry's polygons. See the type's comment in
    `schema/_definitions/maps/01-maps.sql` for the measured distribution.
    """

    ColumnUnit = "column_unit"
    AdjacentColumn = "adjacent_column"
    Footprint = "footprint"
    #: No spatial evidence *exists* -- the lexicon holds no footprint for this
    #: name, so nothing could be tested. Distinct from a name that has a
    #: footprint and failed against it, which is rejected rather than recorded:
    #: absence of evidence is not evidence of absence, but contrary evidence is.
    NoEvidence = "none"


#: The envelope of each legend entry of one source. Shared by every spatial test,
#: and the reason they are cheap: a single grouped aggregate over the source's own
#: polygons, with no spatial join in it. `ST_Extent` accumulates a bounding box as
#: it streams, where the SQL pipeline's `ST_Envelope(ST_Collect(geom))`
#: materializes every polygon first -- 2.6s for all 6,816 of SGMC's entries.
#: `ST_Extent` returns a `box2d`, which carries no SRID, hence `ST_SetSRID`.
_ENVELOPES = """
  env AS (
    SELECT ml.legend_id,
           ST_SetSRID(ST_Extent(p.geom)::geometry, 4326) AS envelope
    FROM maps.legend lg
    JOIN maps.map_legend ml ON ml.legend_id = lg.legend_id
    JOIN {scale_table} p ON p.map_id = ml.map_id
    WHERE lg.source_id = :source_id AND p.source_id = :source_id
    GROUP BY ml.legend_id
  )
"""

_PAIRS = """
  pair AS (
    SELECT legend_id, strat_name_id
    FROM unnest(
      CAST(:legend_ids AS integer[]), CAST(:strat_name_ids AS integer[])
    ) AS t(legend_id, strat_name_id)
  )
"""


def _column_evidence(db, scale, source_id, legend_ids, strat_name_ids, tolerance_km):
    """Pairs whose name is carried by a unit in a column this entry sits on.

    `bool_or` takes the stronger of the two where an entry reaches both a
    containing and an adjacent column.
    """
    return db.run_query(
        f"""
        WITH {_ENVELOPES},
        {_PAIRS},
        col AS (
          SELECT env.legend_id, ca.col_id,
                 ST_Intersects(ca.col_area, env.envelope) AS containing
          FROM env
          JOIN macrostrat.col_areas ca
            ON ST_DWithin(
                 ca.col_area::geography, env.envelope::geography, :tolerance
               )
          JOIN macrostrat.cols c
            ON c.id = ca.col_id AND c.status_code = 'active'
        )
        SELECT pair.legend_id, pair.strat_name_id,
               bool_or(col.containing) AS containing
        FROM pair
        JOIN col ON col.legend_id = pair.legend_id
        JOIN macrostrat.units u ON u.col_id = col.col_id
        JOIN macrostrat.unit_strat_names usn
          ON usn.unit_id = u.id AND usn.strat_name_id = pair.strat_name_id
        GROUP BY 1, 2
        """,
        {
            "scale_table": Identifier("maps", scale),
            "source_id": source_id,
            "legend_ids": legend_ids,
            "strat_name_ids": strat_name_ids,
            "tolerance": tolerance_km * 1000,
        },
    ).all()


def _footprint_evidence(db, scale, source_id, legend_ids, strat_name_ids, buffer):
    """Pairs whose footprint reaches the legend entry's envelope."""
    return db.run_query(
        f"""
        WITH {_ENVELOPES},
        {_PAIRS}
        SELECT DISTINCT pair.legend_id, pair.strat_name_id
        FROM pair
        JOIN env USING (legend_id)
        JOIN macrostrat.strat_name_footprints f USING (strat_name_id)
        WHERE ST_DWithin(f.geom, env.envelope, :buffer)
        """,
        {
            "scale_table": Identifier("maps", scale),
            "source_id": source_id,
            "legend_ids": legend_ids,
            "strat_name_ids": strat_name_ids,
            "buffer": buffer,
        },
    ).all()


def corroborate(
    db: Database,
    slug: str,
    pairs: set,
    *,
    buffer: float = DEFAULT_BUFFER,
    tolerance_km: float = DEFAULT_COLUMN_TOLERANCE_KM,
) -> dict:
    """`(legend_id, strat_name_id) -> (LocationBasis, age_overlaps)`.

    **Match first, then corroborate.** The obvious way round -- decide up front
    which names belong near the source, then match against those -- reads well
    and is wrong at both ends. Blocking on `maps.sources.rgeom` is no constraint
    at all for a national compilation like SGMC, which is what left `Lee
    Formation` matching `Lee Gneiss`; and blocking per legend entry up front
    means intersecting every polygon against every footprint, 312,286 x 48,536
    for SGMC, which does not finish.

    Inverting it makes the same tests cheap. Text matching first narrows SGMC to
    ~30,000 candidate pairs, passed in here as two arrays, and each is then a
    handful of indexed lookups: 2.4s for the column evidence, 2.7s for the
    footprints. Entries touch about six columns each, so the continent-sized
    envelope never materializes.

    **The two spatial tests are separate queries on purpose.** Asked as one, with
    the age comparison joined on as well, SGMC ran for minutes instead of
    seconds. `pair` comes from `unnest`, which the planner estimates at 100 rows
    however many are passed, so joining several materialized CTEs against it
    picks nested loops and goes quadratic. Kept apart, each query is the shape
    that was measured, and the ages are resolved in Python from two small
    lookups rather than joined at all.

    Legend grain is the grain the SQL pipeline used too: its `temp_rocks`
    envelope is grouped by the legend key, not by polygon. It is weaker than
    polygon grain for the column rungs -- "*some* polygon of this entry sits on a
    column carrying this name" -- which is part of why `footprint` still admits
    homonyms like `Newark` and `Brunswick`.
    """
    if not pairs:
        return {}

    source_id = db.run_query(
        "SELECT source_id FROM maps.sources WHERE slug = :slug", dict(slug=slug)
    ).scalar()
    scale = find_scale_table(db, source_id)
    legend_ids, strat_name_ids = (list(v) for v in zip(*sorted(pairs)))
    args = (db, scale, source_id, legend_ids, strat_name_ids)

    basis = {}
    for r in _footprint_evidence(*args, buffer):
        basis[(r.legend_id, r.strat_name_id)] = LocationBasis.Footprint
    # Column evidence outranks a footprint, so it is applied second.
    for r in _column_evidence(*args, tolerance_km):
        basis[(r.legend_id, r.strat_name_id)] = (
            LocationBasis.ColumnUnit if r.containing else LocationBasis.AdjacentColumn
        )

    span = {
        r.legend_id: (r.age_top, r.age_bottom)
        for r in db.run_query(
            """
            SELECT lg.legend_id, ti.age_top, tb.age_bottom
            FROM maps.legend lg
            LEFT JOIN macrostrat.intervals ti ON ti.id = lg.t_interval
            LEFT JOIN macrostrat.intervals tb ON tb.id = lg.b_interval
            WHERE lg.source_id = :source_id
            """,
            dict(source_id=source_id),
        )
    }
    lexicon_age = {
        r.strat_name_id: (r.early_age, r.late_age)
        for r in db.run_query(
            "SELECT strat_name_id, early_age, late_age"
            " FROM macrostrat.lookup_strat_names"
        )
    }

    out = {}
    for pair in pairs:
        legend_id, strat_name_id = pair
        top, bottom = span.get(legend_id, (None, None))
        early, late = lexicon_age.get(strat_name_id, (None, None))
        if None in (top, bottom, early, late):
            age = None
        else:
            age = late <= bottom and early >= top
        out[pair] = (basis.get(pair, LocationBasis.NoEvidence), age)
    return out


def fields_for(row, fields=FIELD_TIERS):
    """Which of `fields` to read for this row.

    All of them. An earlier version read `strat_name` alone wherever it was
    populated, on the reasoning that a curated field cannot be improved on by a
    description. That holds for SGMC, but it is not how NGS is organized, and
    skipping the description there discards real matches for no gain -- the
    tighter test prose has to pass (`_names_a_unit`) is what keeps it honest,
    not the presence of a curated field.

    The field a match came from still rides along with it as `match_field`, so
    the distinction survives where it belongs: in the evidence, not in whether
    the text was read.
    """
    return tuple(f for f in fields if getattr(row, f, None))


@dataclass
class RowMatch:
    #: strat_name_id -> the strongest field it was found in.
    by_id: dict = field(default_factory=dict)
    #: strat_name_id -> the cleaned name that reached it. Without this a match is
    #: a bare integer and cannot be judged by eye.
    keys: dict = field(default_factory=dict)
    #: Ids whose own lithology words are exactly the ones the map text used --
    #: `Aztec Sandstone` for a map that wrote "Aztec Sandstone", as against
    #: `Aztec Quartzite` and `Aztec Granodiorite`, which share the key `aztec`.
    lith_exact: set = field(default_factory=set)
    #: Ids whose lexicon rank agreed with the rank the map text declared.
    #: Evidence, not a filter -- `macrostrat.strat_names.rank` has no `Suite`, so
    #: vetoing on disagreement cost 110 true SGMC matches. It is used to choose
    #: between lexicon entries that describe the same concept; see
    #: `prefer_rank_agreement`.
    rank_agrees: set = field(default_factory=set)
    #: Names that parsed with a rank -- so the text structurally declared a
    #: stratigraphic unit -- and matched nothing in the lexicon. Not a failure of
    #: matching: a formally named unit Macrostrat's lexicon does not carry.
    lexicon_gaps: set = field(default_factory=set)

    def __bool__(self):
        return bool(self.by_id)


def match_text(text: str, lexicon) -> list[tuple[int, bool]]:
    """`(strat_name_id, rank_agrees)` for every lexicon entry this text names.

    Geography is not consulted here; see `corroborate`.
    """
    out = []
    for p, cand in _candidates(text, lexicon):
        agrees = not p.rank or not cand.ranks or p.rank in cand.ranks
        out.append((cand.strat_name_id, agrees))
    return out


def _names_a_unit(p, cand) -> bool:
    """Does this phrase name a stratigraphic unit, or merely describe a rock?

    Asked only of prose. In `strat_name` the answer is given -- the column
    asserts it. In a description it has to be read off the text, because the
    cleaner strips lithology words and leaves the remainder looking the same
    either way: "gray, medium-grained sandstone" reduces to `gray`, which is
    also what `Gray Member` reduces to. Accepting that collision on its own cost
    1,374 false pairs on SGMC, and prose contributed 31,565 pairs while
    accounting for none of the matches the SQL pipeline found.

    Two things count as naming a unit. A rank word is the explicit case -- "the
    Chugwater Formation" says what it is. A lithology that the lexicon entry
    carries in its *own* name is the implicit one: `Ravenswood Granodiorite` has
    no rank word, and the only thing separating it from "gray sandstone" is that
    the lexicon also calls it a granodiorite. That clause recovers 1,235 pairs
    -- `Devine Canyon Ash-flow Tuff`, `Brayman Shale`, `Ste Genevieve Limestone`
    -- every one of them a concept the rank test alone had missed.

    It is not airtight, and cannot be: `Black Shale Member` is a real entry whose
    name is two ordinary words, so any description reading "black shale" claims
    it. Separating those needs evidence the text does not carry.
    """
    if p.rank is not None:
        return True
    return bool(cand.liths & frozenset(p.lith_signifiers))


#: Rank words that are also ordinary descriptive English, and so are weak
#: evidence that a phrase is a formal name.
#:
#: Only `Bed`. "lake bed", "red beds", "stream bed" describe a layer rather than
#: naming one, where "Formation", "Member" and "Group" are almost always formal.
#: "Playa, lake bed, and flood plain deposits" parses as the name `lake` at rank
#: Bed, and `Lower Lake Formation` also cleans to `lake` -- `lower` being a
#: positional term -- so the two met on a word the map never meant as a name.
WEAK_RANKS = frozenset({StratRank.Bed})


def _rank_carries(p, cand) -> bool:
    """For a weak rank word, the lexicon has to agree before it counts.

    Rank is evidence rather than a veto everywhere else, and deliberately so:
    `macrostrat.strat_names.rank` has no `Suite`, and a map may call a Macrostrat
    group a formation, so a general veto cost 110 true SGMC matches. The
    disagreements are mostly real -- `Umpqua Group` -> `Umpqua Formation`,
    `Zion Hill Quartzite Member` -> `Zion Hill Quartzite` are the same units.

    Narrowed to `Bed` it costs nothing and removes a clear class of error: 25
    SGMC matches, **none of which the SQL pipeline found**, among them `mineral`
    -> `Mineral Formation` and `tioga` -> `Tioga Drift`.
    """
    if p.rank not in WEAK_RANKS:
        return True
    return p.rank in cand.ranks


def _candidates(text: str, lexicon, *, prose: bool = False):
    for p in _parse(text):
        for cand in lexicon.get(p.name, ()):
            if not _rank_carries(p, cand):
                continue
            if prose and not _names_a_unit(p, cand):
                continue
            yield p, cand


def _parse(text: str):
    try:
        return clean_strat_name(text, split_hierarchy=True)
    except Exception:
        return []


def match_row(row, lexicon, fields=FIELD_TIERS) -> RowMatch:
    """Match this row's text fields, keeping the strongest field each id came from.

    Text only. The result is a candidate set for `corroborate` to judge.
    Which fields are read is `fields_for`'s decision, not this one's.
    """
    result = RowMatch()
    for tier in fields_for(row, fields):
        text = getattr(row, tier, None)
        if not text:
            continue
        prose = tier not in NAME_FIELDS
        for p, cand in _candidates(text, lexicon, prose=prose):
            result.by_id.setdefault(cand.strat_name_id, tier)
            result.keys.setdefault(cand.strat_name_id, p.name)
            if cand.liths == frozenset(p.lith_signifiers):
                result.lith_exact.add(cand.strat_name_id)
            if p.rank is not None and p.rank in cand.ranks:
                result.rank_agrees.add(cand.strat_name_id)
    result.lexicon_gaps = _gaps(row, lexicon)
    return result


def _gaps(row, lexicon) -> set:
    """Rank-bearing names in this row's authoritative fields that the lexicon lacks.

    Reported, not matched -- candidates for lexicon ingestion.
    """
    gaps: set = set()
    # Gaps are judged on the authoritative fields only. A rank-bearing name in a
    # description is as likely to be a unit from a neighbouring column as one
    # this map failed to link.
    #
    # A rank word is not enough on its own to call something a name. "Albite
    # schist and granofels member of the Hoosac Formation" yields `hoosac` and
    # also `albite`, which is a mineral, not a unit Macrostrat is missing.
    # Vetoing descriptions cuts ngs-vermont's gap list from 60 to 39.
    for tier in ("strat_name", "name"):
        text = getattr(row, tier, None)
        if not text:
            continue
        for p in _parse(text):
            if p.rank is None or p.name in lexicon:
                continue
            if describes_rock(p.name):
                continue
            gaps.add(p.name)
    return gaps


def prefer_exact_name(by_id: dict, keys: dict, lith_exact: set) -> dict:
    """Among the entries one cleaned name reached, keep the ones it names exactly.

    Lithology stripping is what makes this necessary. "Aztec Sandstone" cleans to
    `aztec`, and so do `Aztec Sandstone`, `Aztec Quartzite`, `Aztec Granodiorite`
    and `Aztec Siltstone` -- four different units. The map said *Sandstone*, and
    `lith_signifiers` preserved that on both sides, so the exact one is
    recoverable even though the key is not.

    Grouped by the cleaned name rather than by concept, because these are
    distinct concepts and the whole point is to choose between them. Applied only
    where some entry matches exactly, so a name whose lithology the lexicon never
    uses is left whole rather than emptied.
    """
    grouped: dict = defaultdict(list)
    for strat_name_id in by_id:
        grouped[keys.get(strat_name_id, strat_name_id)].append(strat_name_id)

    kept = {}
    for ids in grouped.values():
        exact = [i for i in ids if i in lith_exact]
        for i in exact or ids:
            kept[i] = by_id[i]
    return kept


def prefer_rank_agreement(by_id: dict, rank_agrees: set, concepts: dict) -> dict:
    """Within one concept, keep the entries whose rank the map text confirmed.

    Lithology stripping collapses `Hampton Formation`, `Hampton Group`, `Hampton
    Shale` and `Hampton Sandstone` onto the single key `hampton`, so a map
    reading "Hampton Formation" matches all four and the output carries two
    lexicon ids per concept where the SQL pipeline carried 1.25. Nothing in the
    name can separate them -- but the rank can, and the map said `Formation`.

    Applied only where some entry for that concept agrees, so a concept whose
    entries all disagree is left whole rather than emptied. On SGMC this takes
    the match count from 1.79x the SQL pipeline's to 1.60x without changing the
    concept count at all.

    Entries with no concept are keyed on their own id, so they are never grouped
    with anything else.
    """
    grouped: dict = defaultdict(list)
    for strat_name_id, tier in by_id.items():
        grouped[concepts.get(strat_name_id, ("id", strat_name_id))].append(
            strat_name_id
        )

    kept = {}
    for ids in grouped.values():
        agreeing = [i for i in ids if i in rank_agrees]
        for i in agreeing or ids:
            kept[i] = by_id[i]
    return kept


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


def legend_rows(db: Database, slug: str):
    return db.run_query(
        """
        SELECT lg.legend_id, lg.name, lg.strat_name, lg.descrip,
               lg.strat_name_ids
        FROM maps.legend lg JOIN maps.sources s ON s.source_id = lg.source_id
        WHERE s.slug = :slug
        """,
        dict(slug=slug),
    ).all()


@dataclass
class Match:
    """One row of `maps.legend_strat_names`, before it is written."""

    legend_id: int
    strat_name_id: int
    match_field: str
    #: The cleaned name from the map text that reached this lexicon entry.
    matched_text: str
    rank_agrees: bool | None
    location_basis: LocationBasis
    age_overlaps: bool | None


def match_source(
    db: Database, slug: str, lexicon, *, fields=FIELD_TIERS, **kw
) -> list[Match]:
    """Every match this source's legend supports, judged but not yet written.

    Text first, then geography and time -- see `corroborate` for why that order.

    `fields` narrows which legend columns are read. Matching one field alone is
    how a source whose descriptions carry the names -- NGS lumps units as
    "Includes units such as X, Y and Z" -- can be matched without its `name`
    column diluting the result, and how the contribution of a field can be
    measured on its own.
    """
    rows = legend_rows(db, slug)
    concepts = dict(
        db.run_query(
            "SELECT strat_name_id, concept_id FROM macrostrat.lookup_strat_names"
            " WHERE concept_id IS NOT NULL"
        ).all()
    )
    matched = {r.legend_id: match_row(r, lexicon, fields) for r in rows}
    for m in matched.values():
        m.by_id = prefer_exact_name(m.by_id, m.keys, m.lith_exact)
        m.by_id = prefer_rank_agreement(m.by_id, m.rank_agrees, concepts)

    pairs = {(lid, i) for lid, m in matched.items() for i in m.by_id}
    judged = corroborate(db, slug, pairs, **kw)

    # A name with a footprint that does not reach this source has been tested and
    # failed, and is dropped. A name with no footprint at all was never testable,
    # and is kept at `none` if its reference allows -- see `unplaced_allowed`.
    untestable = unplaced_allowed(db, slug)

    out = []
    for lid, m in matched.items():
        for strat_name_id, field in m.by_id.items():
            basis, age = judged.get(
                (lid, strat_name_id), (LocationBasis.NoEvidence, None)
            )
            if basis is LocationBasis.NoEvidence and strat_name_id not in untestable:
                continue
            out.append(
                Match(
                    legend_id=lid,
                    strat_name_id=strat_name_id,
                    match_field=field,
                    matched_text=m.keys.get(strat_name_id, ""),
                    rank_agrees=strat_name_id in m.rank_agrees,
                    location_basis=basis,
                    age_overlaps=age,
                )
            )
    return out


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


def write_matches(db: Database, slug: str, matches: list) -> tuple[int, int, int]:
    """Bring this source's matches into line with `matches`.

    **A merge, not a replace.** Matching is re-run whenever the lexicon or a
    description changes, and most of what it finds is what it found last time:
    deleting and re-inserting churned every unchanged row and reset every
    `matched_at`, so the column recorded the last run rather than when the match
    was established.

    Unlike `maps.legend_liths`, where the row is its own key, this table has a
    payload -- `rank_agrees`, `location_basis`, `age_overlaps` -- so the merge is
    a real update. The `WHERE` on the `DO UPDATE` is what makes it one: a row
    whose evidence is unchanged is not written at all, and only a row that
    actually moved gets a new `matched_at`. `IS DISTINCT FROM` rather than `<>`
    because all three are nullable.

    Manual matches are untouched on every path. `is_manual` means a human
    asserted it and no matcher may withdraw it, so the update skips them and the
    delete excludes them -- what the old pipeline expressed as the string test
    `basis_col NOT LIKE 'manual%'`.

    Everything runs inside one transaction, staging included: `db.transaction()`
    takes a connection of its own and rebinds `db.session` to it, so a temporary
    table created before the block belongs to a different connection and is not
    visible inside it. The staging table is `ON COMMIT DROP` because that
    connection comes from a pool and keeps its temporary tables when handed
    back -- without it the next source in a sweep finds the table already
    there.

    Returns `(inserted, updated, removed)`.
    """
    rows = [
        {
            "legend_id": m.legend_id,
            "strat_name_id": m.strat_name_id,
            "match_field": m.match_field,
            "rank_agrees": m.rank_agrees,
            "location_basis": m.location_basis.value,
            "age_overlaps": m.age_overlaps,
        }
        for m in matches
    ]

    with db.transaction():
        db.run_sql(
            """
            CREATE TEMPORARY TABLE legend_strat_name_matches (
              legend_id integer NOT NULL,
              strat_name_id integer NOT NULL,
              match_field maps.strat_name_match_field NOT NULL,
              rank_agrees boolean,
              location_basis maps.strat_name_location_basis,
              age_overlaps boolean
            ) ON COMMIT DROP
            """
        )
        if rows:
            db.run_query(
                """
                INSERT INTO legend_strat_name_matches (
                  legend_id, strat_name_id, match_field,
                  rank_agrees, location_basis, age_overlaps
                ) VALUES (
                  :legend_id, :strat_name_id,
                  CAST(:match_field AS maps.strat_name_match_field),
                  :rank_agrees,
                  CAST(:location_basis AS maps.strat_name_location_basis),
                  :age_overlaps
                )
                """,
                rows,
            )

        # `xmax = 0` is true only of a tuple this statement inserted, which is
        # how an upsert tells its two outcomes apart.
        written = db.run_query(
            """
            INSERT INTO maps.legend_strat_names (
              legend_id, strat_name_id, match_field,
              rank_agrees, location_basis, age_overlaps
            )
            SELECT legend_id, strat_name_id, match_field,
                   rank_agrees, location_basis, age_overlaps
            FROM legend_strat_name_matches
            ON CONFLICT (legend_id, strat_name_id, match_field) DO UPDATE
              SET rank_agrees = EXCLUDED.rank_agrees,
                  location_basis = EXCLUDED.location_basis,
                  age_overlaps = EXCLUDED.age_overlaps,
                  matched_at = now()
              WHERE NOT maps.legend_strat_names.is_manual
                AND (
                  maps.legend_strat_names.rank_agrees
                    IS DISTINCT FROM EXCLUDED.rank_agrees
                  OR maps.legend_strat_names.location_basis
                    IS DISTINCT FROM EXCLUDED.location_basis
                  OR maps.legend_strat_names.age_overlaps
                    IS DISTINCT FROM EXCLUDED.age_overlaps
                )
            RETURNING (xmax = 0) AS inserted
            """
        ).all()

        removed = db.run_query(
            """
            DELETE FROM maps.legend_strat_names lsn
            USING maps.legend lg
            WHERE lsn.legend_id = lg.legend_id
              AND lg.source_id = (
                SELECT source_id FROM maps.sources WHERE slug = :slug
              )
              AND NOT lsn.is_manual
              AND NOT EXISTS (
                SELECT 1 FROM legend_strat_name_matches m
                WHERE m.legend_id = lsn.legend_id
                  AND m.strat_name_id = lsn.strat_name_id
                  AND m.match_field = lsn.match_field
              )
            """,
            dict(slug=slug),
        ).rowcount

    inserted = sum(1 for r in written if r.inserted)
    return inserted, len(written) - inserted, removed


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
    """Load the vocabularies the normalizer and the gap test need, then the lexicon."""
    create_ignore_list(
        db.run_query("SELECT lith FROM macrostrat.liths").scalars().all()
    )
    words: set[str] = set()
    for query in (
        "SELECT lith FROM macrostrat.liths",
        "SELECT lith_att FROM macrostrat.lith_atts",
        "SELECT mineral FROM macrostrat.minerals",
    ):
        for value in db.run_query(query).scalars():
            if value:
                words.update(value.lower().split())
    _descriptors.set(frozenset(words))
    return build_lexicon(db)
