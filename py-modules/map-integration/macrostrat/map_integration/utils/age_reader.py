"""Reading a legend's age text -- "Oligocene to Lower Miocene", "Permain",
"< 2 Ma" -- as Macrostrat intervals.

The GeMS ingest's matcher (`gems_utils.lookup_and_validate_age`) keeps only the
first interval of a range in a sentence ("(Oligocene to Lower Miocene)" is
Oligocene alone) and needs every word spelled as Macrostrat spells it. This
reads:

- a range as a range: parts joined by to, or, and, a comma or a hyphen, a
  qualifier taking the next part's period where it has none ("Late to early
  Holocene");
- lower and upper as early and late, latest and earliest likewise; a qualified
  name Macrostrat lacks ("Late Holocene") as its period alone; Early, Middle
  and Late Proterozoic as Paleo-, Meso- and Neoproterozoic; recent and modern
  as the Holocene, Oligo- as the Oligocene;
- a misspelt interval as the one it is a letter or two off ("Hiolocene",
  "Mesoproterozioc", "Teriary", "Permain", "Pennsyvanian");
- an age in years ("< 2 Ma", "~10 Ma", "10 to 130 ka") as the international
  epochs it falls in.

`b_interval` is the oldest interval read, `t_interval` the youngest.
"""

import re
from difflib import get_close_matches
from typing import Optional

QUALIFIERS = {
    "early": "early",
    "earliest": "early",
    "lower": "early",
    "middle": "middle",
    "mid": "middle",
    "late": "late",
    "latest": "late",
    "upper": "late",
}

#: Age words Macrostrat's intervals do not have, as the interval they mean.
#: Not "historical": a historical unit is not always the whole Holocene.
PERIOD_ALIASES = {
    "modern": "holocene",
    "recent": "holocene",
    "oligo": "oligocene",
}

#: A qualified name for the one Macrostrat has.
QUALIFIED_ALIASES = {
    "early proterozoic": "paleoproterozoic",
    "middle proterozoic": "mesoproterozoic",
    "late proterozoic": "neoproterozoic",
}

#: Unit names whose age is known though the name gives none, matched whole.
NAMED_AGES = {
    "historical river terrace deposits": "holocene",
}

CONNECTORS = {"to", "or", "and", "-", ","}

#: How close a misspelling must be to the interval it is taken for, and the
#: shortest word that is corrected at all.
TYPO_CUTOFF = 0.85
TYPO_MIN_LENGTH = 5

#: An age in years: "< 2 Ma", "~10 Ma", "10 to 130 ka", "<150 years".
#: A number may have thousands separators ("1,000 ka").
_NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_YEARS = re.compile(
    rf"(?P<under><|less than|younger than)?\s*[~≈]?\s*(?P<a>{_NUMBER})\s*"
    rf"(?:(?:to|-|–|—)\s*[~≈]?\s*(?P<b>{_NUMBER})\s*)?"
    r"(?P<unit>ma|ka|m\.?y\.?|years?|yrs?)\b",
    re.I,
)
_UNIT_MA = {"ma": 1.0, "my": 1.0, "m.y.": 1.0, "m.y": 1.0, "ka": 1e-3}

_WORD = re.compile(r"[A-Za-z]+|-|,")

#: The international timescales: misspellings are corrected to their names,
#: and ages in years read as their epochs.
INTERNATIONAL = [
    "international eons",
    "international eras",
    "international periods",
    "international epochs",
    "international ages",
]


def _dashes(text: str) -> str:
    """En and em dashes as hyphens: "Lower Cretaceous – Jurassic" is a range."""
    return text.replace("–", "-").replace("—", "-")


class AgeReader:
    """Macrostrat's intervals, and reading an age phrase against them."""

    def __init__(self, db):
        rows = db.run_query(
            """
            SELECT i.id, i.interval_name, i.age_bottom, i.age_top, i.interval_type,
                EXISTS (
                    SELECT 1 FROM macrostrat.timescales_intervals ti
                    JOIN macrostrat.timescales t ON t.id = ti.timescale_id
                    WHERE ti.interval_id = i.id
                      AND t.timescale = ANY(CAST(:international AS text[]))
                ) AS international,
                EXISTS (
                    SELECT 1 FROM macrostrat.timescales_intervals ti
                    JOIN macrostrat.timescales t ON t.id = ti.timescale_id
                    WHERE ti.interval_id = i.id
                      AND t.timescale = 'international epochs'
                ) AS epoch
            FROM macrostrat.intervals i
            -- An international interval wins a name it shares.
            ORDER BY international DESC, i.id
            """,
            dict(international=INTERNATIONAL),
        ).all()
        self.ids: dict[str, int] = {}
        self.ages: dict[int, tuple[float, float]] = {}
        self.names: dict[int, str] = {}
        self.epochs: list[int] = []
        spelling = set()
        for row in rows:
            name = str(row.interval_name).lower()
            self.ids.setdefault(name, int(row.id))
            self.ages[int(row.id)] = (float(row.age_bottom), float(row.age_top))
            self.names[int(row.id)] = row.interval_name
            if row.epoch:
                self.epochs.append(int(row.id))
            if row.international or row.interval_type in ("period", "era", "eon"):
                spelling.update(w for w in name.split() if w.isalpha())
        # One-word interval names, the periods a qualifier can go with.
        self.periods = {n for n in self.ids if " " not in n} | set(PERIOD_ALIASES)
        self.spelling = sorted(spelling - set(QUALIFIERS))

    def find(self, name: str) -> Optional[tuple[str, int, int]]:
        """(the age as written, b_interval, t_interval) a unit's name gives: a
        name in `NAMED_AGES`, else an age in parentheses ("Dacite lava flows
        (Oligocene to Lower Miocene)", "(~10 Ma)"), else one the name starts
        with ("Late Miocene to Pliocene Quiburis deposits").

        Not one in the middle of a name, which is as often another unit's:
        "Regolith derived from Miocene conglomerate".
        """
        if not name:
            return None
        named = NAMED_AGES.get(re.sub(r"\s+", " ", name).strip().lower())
        if named is not None:
            interval = self.ids[named]
            return self.names[interval], interval, interval
        for text in re.findall(r"\(([^()]*(?:\(\?\)[^()]*)*)\)", name)[::-1]:
            if self._all_age(text) or _YEARS.search(text):
                found = self.read(text)
                if found is not None:
                    return (re.sub(r"\s+", " ", text).strip(), *found)
        phrase = self._leading(name)
        if phrase:
            found = self.read(phrase)
            if found is not None:
                return (phrase, *found)
        return None

    def read(self, phrase: str) -> Optional[tuple[int, int]]:
        """(b_interval, t_interval) for an age phrase, or None."""
        if not phrase:
            return None
        found = self._intervals(self._words(phrase))
        if not found:
            found = self._years(phrase)
        if not found:
            return None
        b = max(found, key=lambda i: self.ages[i][0])
        t = min(found, key=lambda i: self.ages[i][1])
        return b, t

    def as_written(self, phrase: str) -> bool:
        """Whether `phrase` reads as intervals with every word as written: not
        corrected ("Permain"), not an age in years ("< 2 Ma")."""
        if not phrase:
            return False
        text = _dashes(phrase).lower().replace("(?)", " ").replace("?", " ")
        words = _WORD.findall(text)
        if any(self._word(w) != w for w in words):
            return False
        return bool(self._intervals(words))

    def legend(self, age, *names) -> Optional[tuple[int, int, Optional[str]]]:
        """(b_interval, t_interval, age) for a legend entry: from its `age`,
        else from the first of `names` (name, fullname) that gives one. The
        age is the entry's own where it reads as written, otherwise the
        intervals' names ("Permain", "< 2 Ma" or no age at all become
        "Permian", "Pleistocene to Holocene", ...)."""
        age = None if age is None or str(age).strip() == "" else str(age)
        found = self.read(age) if age else None
        if found is not None:
            b, t = found
            return b, t, age if self.as_written(age) else self.label(b, t)
        for name in names:
            hit = self.find(None if name is None else str(name))
            if hit is not None:
                b, t = hit[1:]
                return b, t, self.label(b, t)
        return None

    def label(self, b: int, t: int) -> str:
        """The interval names, as `age` is written: "Holocene", "Pleistocene to
        Holocene"."""
        return self.names[b] if b == t else f"{self.names[b]} to {self.names[t]}"

    def _word(self, word: str) -> str:
        """A word as Macrostrat spells it: an age word as it is, a misspelt
        interval as the one it is closest to, anything else as it is."""
        if (
            word in QUALIFIERS
            or word in self.periods
            or word in CONNECTORS
            or len(word) < TYPO_MIN_LENGTH
        ):
            return word
        close = get_close_matches(word, self.spelling, n=1, cutoff=TYPO_CUTOFF)
        return close[0] if close else word

    def _words(self, text: str) -> list[str]:
        text = _dashes(text).lower().replace("(?)", " ").replace("?", " ")
        return [self._word(w) for w in _WORD.findall(text)]

    def _is_age(self, word: str) -> bool:
        return word in QUALIFIERS or word in self.periods or word in CONNECTORS

    def _all_age(self, text: str) -> bool:
        words = self._words(text)
        return bool(words) and all(map(self._is_age, words))

    def _leading(self, name: str) -> Optional[str]:
        """The run of age words a name starts with, ending on a period: "Late
        Miocene to Pliocene", not "Middle to" of "Middle to fine grained"."""
        tokens = _WORD.findall(_dashes(name).replace("(?)", " "))
        run = []
        for token in tokens:
            if not self._is_age(self._word(token.lower())):
                break
            run.append(token)
        while run and self._word(run[-1].lower()) not in self.periods:
            run.pop()
        return " ".join(run).replace(" - ", "-").replace(" ,", ",") or None

    def _intervals(self, words: list[str]) -> list[int]:
        parts = [[]]
        for word in words:
            if word in CONNECTORS:
                parts.append([])
            else:
                parts[-1].append(word)
        parts = [p for p in parts if p]
        found = []
        for i, part in enumerate(parts):
            # The qualifier next to the period: "early middle Pleistocene" is
            # the Middle Pleistocene.
            qualifiers = [QUALIFIERS[w] for w in part if w in QUALIFIERS]
            qualifier = qualifiers[-1] if qualifiers else None
            period = next((w for w in part if w in self.periods), None)
            if period is None:
                # A qualifier on its own takes the next part's period: "late
                # to early Holocene".
                period = next(
                    (w for later in parts[i + 1 :] for w in later if w in self.periods),
                    None,
                )
            if period is None:
                continue
            period = PERIOD_ALIASES.get(period, period)
            qualified = f"{qualifier} {period}" if qualifier else period
            qualified = QUALIFIED_ALIASES.get(qualified, qualified)
            interval = self.ids.get(qualified, self.ids.get(period))
            if interval is not None:
                found.append(interval)
        return found

    def _years(self, text: str) -> list[int]:
        """The international epochs an age in years spans."""
        match = _YEARS.search(text)
        if match is None:
            return []
        unit = match["unit"].lower().replace(" ", "")
        scale = _UNIT_MA.get(unit, 1e-6)  # years
        ages = [float(match["a"].replace(",", "")) * scale]
        if match["b"] is not None:
            ages.append(float(match["b"].replace(",", "")) * scale)
        if match["under"]:
            ages.append(0.0)
        oldest, youngest = max(ages), min(ages)
        b = next(
            (i for i in self.epochs if self.ages[i][1] < oldest <= self.ages[i][0]),
            None,
        )
        t = next(
            (i for i in self.epochs if self.ages[i][1] <= youngest < self.ages[i][0]),
            None,
        )
        return [i for i in (b, t) if i is not None]
