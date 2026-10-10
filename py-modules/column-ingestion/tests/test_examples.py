"""`macrostrat columns create-examples`: the format's examples, ingested as a standing test."""

from pathlib import Path

import pytest

from macrostrat.column_ingestion.examples import (
    examples_dir,
    find_examples,
    ingest_examples,
    resolve_example,
)

EXAMPLES = examples_dir(Path(__file__).parents[3])
HOGAN = EXAMPLES / "hogan-2011-marble-mountains.xlsx"


def test_find_examples_skips_lock_files(tmp_path):
    for name in ("b.xlsx", "a.xlsx", "~$a.xlsx", "notes.md"):
        (tmp_path / name).touch()
    assert [p.name for p in find_examples(tmp_path)] == ["a.xlsx", "b.xlsx"]


def test_resolve_example(tmp_path):
    (tmp_path / "a.xlsx").touch()
    assert resolve_example("a.xlsx", tmp_path) == tmp_path / "a.xlsx"
    assert resolve_example(tmp_path / "a.xlsx", Path("/nowhere")) == tmp_path / "a.xlsx"
    with pytest.raises(FileNotFoundError):
        resolve_example("missing.xlsx", tmp_path)


@pytest.mark.skipif(
    not HOGAN.exists(), reason="column-ingestion submodule not checked out"
)
class TestIngestExamples:
    def test_rerun_replaces_the_example(self, db, default_age_model_ref):
        for _ in range(2):
            [result] = ingest_examples(db, [HOGAN], project="Test Examples")
            assert result.status == "written", result.notices
        columns = db.run_query(
            "SELECT count(*) FROM macrostrat.cols c"
            " JOIN macrostrat.projects p ON p.id = c.project_id"
            " JOIN macrostrat.col_groups g ON g.id = c.col_group_id"
            " WHERE p.project = 'Test Examples'"
            " AND g.col_group = 'hogan-2011-marble-mountains'"
        ).scalar()
        assert columns == result.summary["n_columns"] == 9
        statuses = (
            db.run_query(
                "SELECT DISTINCT c.status_code FROM macrostrat.cols c"
                " JOIN macrostrat.projects p ON p.id = c.project_id"
                " WHERE p.project = 'Test Examples'"
            )
            .scalars()
            .all()
        )
        assert statuses == ["active"]

    def test_lookups_are_refreshed(self, db, default_age_model_ref):
        """The website reads units through the lookup tables; ingesting fills them."""
        ingest_examples(db, [HOGAN], project="Test Examples")
        units = (
            "SELECT us.unit_id FROM macrostrat.units_sections us"
            " JOIN macrostrat.cols c ON c.id = us.col_id"
            " JOIN macrostrat.col_groups g ON g.id = c.col_group_id"
            " WHERE g.col_group = 'hogan-2011-marble-mountains'"
        )
        n_units = db.run_query(f"SELECT count(*) FROM ({units}) u").scalar()
        attrs = (
            db.run_query(
                "SELECT convert_from(lith, 'UTF8') FROM macrostrat.lookup_unit_attrs_api"
                f" WHERE unit_id IN ({units})"
            )
            .scalars()
            .all()
        )
        n_lookup = db.run_query(
            f"SELECT count(*) FROM macrostrat.lookup_units WHERE unit_id IN ({units})"
        ).scalar()
        assert len(attrs) == n_lookup == n_units == 73
        assert all(lith != "[]" for lith in attrs), "every Hogan unit has a lithology"

    def test_a_failing_example_is_reported_not_raised(
        self, db, default_age_model_ref, tmp_path
    ):
        broken = tmp_path / "broken.xlsx"
        broken.write_bytes(b"not a workbook")
        [result] = ingest_examples(db, [broken], project="Test Examples")
        assert result.status == "failed"
        assert result.exception is not None
