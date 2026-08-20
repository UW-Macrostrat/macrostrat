"""Depositional environments: parsing the `environment` field and resolving it.

Mirrors `lithologies` — a processor holding the lookup table, called with a cell's text
and returning a set — but is simpler, because environments carry no attributes. Each
token is one environment, so there is nothing to disambiguate within an entry.

Syntax, following the workbook contract the legacy importer documented: `;` separates
entries, and each entry is either an `environs.id` or an environment name.

**Tokens resolve to `environs` rows and nothing else.** `environ_class` (`marine` /
`non-marine`) and `environ_type` (`carbonate`, `siliciclastic`, …) are descriptive
attributes of an environment, never match targets. It is easy to misread `marine` as a
class because two environments are named after their own class — ids 38 (`marine`) and 88
(`non-marine`), both with an empty `environ_type` — but those are ordinary rows in
`environs`, and matching `marine` yields that row. No `environ_type` value exists as an
environment name, so a token like `carbonate` matches nothing and is reported.

Unlike `LithsProcessor`, matching here is **exact** on name or id rather than greedy
multi-word matching. Environment vocabulary is a controlled list (`marine`,
`shallow subtidal`, `shoreface`, …) rather than prose, so a token that does not match is
much more likely to be a typo than something to be pattern-matched out of a sentence —
and an unrecognised environment is reported rather than dropped.
"""

from dataclasses import dataclass

from macrostrat.utils import get_logger

from .database import get_all_environs

log = get_logger(__name__)


@dataclass
class Environ:
    """A depositional environment from `macrostrat.environs`."""

    id: int
    name: str
    #: Descriptive only — see the module docstring. Neither of these is a match target.
    type: str | None = None
    environ_class: str | None = None

    def __hash__(self):
        return hash(self.id)


class UnknownEnvironError(ValueError):
    """An environment token matched nothing in `macrostrat.environs`."""


def split_environments(text: str | None) -> list[str]:
    """Split an `environment` cell into its entries."""
    if text is None:
        return []
    return [part.strip() for part in str(text).split(";") if part.strip()]


class EnvironsProcessor:
    """Resolve environment text against `macrostrat.environs`.

    Holds the lookup table so it is fetched once per ingest rather than per unit.
    """

    def __init__(self, db):
        rows = get_all_environs(db)
        self.environs = [
            Environ(
                id=row.id,
                name=row.name,
                type=row.type or None,
                environ_class=row.environ_class or None,
            )
            for row in rows
        ]
        self._by_name = {e.name.lower(): e for e in self.environs}
        self._by_id = {e.id: e for e in self.environs}

    def __call__(self, text: str | None) -> set[Environ]:
        return self.process_text(text)

    def process_text(self, text: str | None) -> set[Environ]:
        """Resolve every entry in an `environment` cell.

        Unmatched tokens are collected and reported together, so a workbook with several
        typos surfaces them in one pass.
        """
        found: set[Environ] = set()
        unknown: list[str] = []
        for token in split_environments(text):
            environ = self.match(token)
            if environ is None:
                unknown.append(token)
            else:
                found.add(environ)
        if unknown:
            raise UnknownEnvironError(
                "unrecognised environment(s): " + ", ".join(repr(t) for t in unknown)
            )
        return found

    def match(self, token: str) -> Environ | None:
        """Match a single token against `environs`, by id or by name.

        Names are matched case-insensitively. Only `environs.environ` and `environs.id`
        are consulted — never `environ_class` or `environ_type`.
        """
        token = token.strip()
        if token.isdigit():
            return self._by_id.get(int(token))
        return self._by_name.get(token.lower())
