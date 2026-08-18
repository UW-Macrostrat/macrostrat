"""References: the `refs` sheet, `macrostrat.refs`, and the `col_refs` links.

A workbook's `refs` sheet carries its own local `ref_id` values, which columns cite in a
comma-separated `ref_ids` field. Neither is a database id, so ingesting references means
resolving the workbook's local ids onto `macrostrat.refs` rows and then linking columns
through `macrostrat.col_refs`.

`refs` is shared across projects — the same publication may already be there from another
import — so the natural key is the citation itself, `(pub_year, author, ref)`, following
the legacy importer. `ref` is a composed citation string: the title, then the publication,
joined with `". "`.

`col_refs` is the one table in this work with a **real** unique constraint,
`UNIQUE (col_id, ref_id)`, so its links do not need the natural-key machinery — but they
do still need dereferenced links removed when a column stops citing something.
"""

from dataclasses import dataclass

import polars as pl

from macrostrat.utils import get_logger

from .database import get_macrostrat_table
from .reconciliation import (
    ReconciliationPlan,
    apply_reconciliation,
    plan_reconciliation,
    reconcile,
)

log = get_logger(__name__)

REF_KEY = ("pub_year", "author", "ref")
#: `rgeom` is a reference's own geometry, curated elsewhere and not ours to write.
REF_COLUMNS = ("doi", "url", "compilation_code")


@dataclass
class Reference:
    """A reference as the workbook describes it."""

    local_id: str
    pub_year: int
    author: str
    ref: str
    doi: str | None = None
    url: str | None = None
    compilation_code: str = ""

    def row(self) -> dict:
        return {
            "pub_year": self.pub_year,
            "author": self.author,
            "ref": self.ref,
            "doi": self.doi,
            "url": self.url,
            "compilation_code": self.compilation_code,
        }


class ReferenceError(ValueError):
    """A workbook's references are unusable."""


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def compose_citation(title: str | None, publication: str | None) -> str:
    """`refs.ref` is a citation string built from the title and the publication."""
    return ". ".join(p for p in (_text(title), _text(publication)) if p)


def parse_ref_ids(value) -> list[str]:
    """Columns cite references as a comma-separated list of workbook-local ids."""
    if value is None:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def get_reference_data(data_file) -> list[Reference]:
    """Read the `refs` sheet.

    Validation problems are collected and reported together rather than one per run.
    """
    df = pl.read_excel(data_file, sheet_name="refs")

    references, problems, seen = [], [], set()
    for number, row in enumerate(df.iter_rows(named=True), start=2):
        local_id = _text(row.get("ref_id"))
        label = f"refs row {number}"

        if local_id is None:
            problems.append(f"{label}: missing `ref_id`")
            continue
        if local_id in seen:
            problems.append(f"{label}: duplicate `ref_id` {local_id!r}")
            continue
        seen.add(local_id)

        author = _text(row.get("authors")) or _text(row.get("author"))
        title = _text(row.get("title"))
        year = _text(row.get("date"))

        if author is None:
            problems.append(f"{label}: `authors` (or `author`) must be non-empty")
        if title is None:
            problems.append(f"{label}: `title` must be non-empty")
        try:
            pub_year = int(float(year)) if year is not None else None
        except ValueError:
            pub_year = None
        if pub_year is None:
            problems.append(f"{label}: `date` must be an integer year, got {year!r}")

        if author is None or title is None or pub_year is None:
            continue

        references.append(
            Reference(
                local_id=local_id,
                pub_year=pub_year,
                author=author,
                ref=compose_citation(title, row.get("publication")),
                doi=_text(row.get("doi")),
                url=_text(row.get("url")),
                # NOT NULL, and an enum whose empty member means "not a compilation".
                compilation_code=_text(row.get("compilation")) or "",
            )
        )

    if problems:
        raise ReferenceError(
            f"{len(problems)} problem(s) in the refs sheet:\n  " + "\n  ".join(problems)
        )
    return references


def reconcile_references(db, references: list[Reference]) -> dict[str, int]:
    """Reconcile `macrostrat.refs`, returning `{workbook ref_id: refs.id}`.

    Existing rows are looked up by citation rather than scoped to a project, since a
    reference may already be present from an unrelated import — and are never deleted for
    the same reason: other projects' columns may cite them.
    """
    if not references:
        return {}

    desired = [ref.row() for ref in references]
    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, pub_year, author, ref, doi, url, compilation_code
            FROM macrostrat.refs
            WHERE (pub_year, author, ref) IN (
                SELECT * FROM unnest(
                    CAST(:years AS integer[]),
                    CAST(:authors AS text[]),
                    CAST(:refs AS text[])
                )
            )
            ORDER BY id
            """,
            {
                "years": [r["pub_year"] for r in desired],
                "authors": [r["author"] for r in desired],
                "refs": [r["ref"] for r in desired],
            },
        )
    ]

    plan = plan_reconciliation(
        existing, desired, key=REF_KEY, owned_columns=REF_COLUMNS
    )
    # A reference not cited by this workbook may still be cited elsewhere. The query above
    # only fetches citations this workbook mentions, so `deletes` should be empty anyway —
    # clear it explicitly so the intent is on the record rather than incidental.
    plan.deletes = []

    ids = apply_reconciliation(
        db, get_macrostrat_table(db, "refs"), plan, desired, owned_columns=REF_COLUMNS
    )
    mapping = {ref.local_id: ref_id for ref, ref_id in zip(references, ids)}
    log.info("refs: %s", plan)
    return mapping


def reconcile_column_references(
    db, col_id: int, ref_ids: list[int]
) -> ReconciliationPlan:
    """Reconcile one column's `col_refs` links."""
    existing = [
        dict(row._mapping)
        for row in db.run_query(
            """
            SELECT id, col_id, ref_id FROM macrostrat.col_refs
            WHERE col_id = :col_id ORDER BY id
            """,
            dict(col_id=col_id),
        )
    ]
    # Deduplicate: `UNIQUE (col_id, ref_id)` means a repeated citation is one link.
    desired = [
        {"col_id": col_id, "ref_id": ref_id} for ref_id in dict.fromkeys(ref_ids)
    ]
    plan, _ = reconcile(
        db,
        get_macrostrat_table(db, "col_refs"),
        existing=existing,
        desired=desired,
        key=("col_id", "ref_id"),
        owned_columns=(),  # a pure link: presence is the whole content
    )
    return plan


def resolve_column_references(db, columns: list, ref_map: dict[str, int]) -> None:
    """Link every column to the references it cites, reporting unknown ids together."""
    problems = []
    for col in columns:
        ref_ids, unknown = [], []
        for local_id in col.ref_ids:
            if local_id in ref_map:
                ref_ids.append(ref_map[local_id])
            else:
                unknown.append(local_id)
        if unknown:
            problems.append(
                f"column {col.local_id or col.name!r} cites unknown ref_id(s): "
                + ", ".join(unknown)
            )
            continue
        reconcile_column_references(db, col.id, ref_ids)

    if problems:
        raise ReferenceError(
            f"{len(problems)} column(s) cite references not in the refs sheet:\n  "
            + "\n  ".join(problems)
        )
