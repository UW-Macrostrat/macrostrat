"""The ingest result: dry runs, graded notices and JSON submissions.

Shared fixtures (`db`, `excel_file`, `test_project`, `default_age_model_ref`) come from
`conftest.py`; `FIXTURES` points at the TSV tables the workbook is assembled from.
"""

import json
from pathlib import Path

import polars as pl
from pytest import fixture, raises

from macrostrat.column_ingestion.database import ProjectIdentifier
from macrostrat.column_ingestion.ingest import (
    Placement,
    ingest_column_data,
    ingest_columns_from_file,
)
from macrostrat.column_ingestion.notices import IngestValidationError

EXCERPT = Path(__file__).parent / "fixtures" / "macrostrat_import_v3_excerpt"


def _table(name: str) -> list[dict]:
    return pl.read_csv(EXCERPT / f"{name}.tsv", separator="\t").to_dicts()


@fixture
def workbook_data() -> dict:
    """The fixture workbook as the JSON an editor would submit."""
    meta = pl.read_csv(
        EXCERPT / "metadata.tsv",
        separator="\t",
        has_header=False,
        new_columns=["key", "value"],
    )
    return {
        "metadata": dict(zip(meta["key"], meta["value"])),
        "columns": _table("columns"),
        "units": _table("units"),
        "refs": _table("refs"),
    }


def _count(db, table: str) -> int:
    return db.run_query(f"SELECT count(*) FROM macrostrat.{table}").scalar()


class TestDryRun:
    def test_dry_run_shows_the_data_and_persists_nothing(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        result = ingest_columns_from_file(db, excel_file, dry_run=True)

        assert result["dry_run"] is True
        assert result["ok"] is True
        assert result["summary"]["n_units"] == 6
        # The result travels through a JSON task backend
        json.dumps(result)

        data = result["data"]
        assert len(data["columns"]) == len(_table("columns"))
        assert len(data["units"]) == 6
        assert len(data["boundaries"]) > 0, "the dry run builds the age model too"
        # Ids made inside a rolled-back transaction mean nothing: they come back
        # provisional, which the editor reads as "not yet written"
        assert all(u["unit_id"] < 0 for u in data["units"])
        assert all(b["boundary_id"] < 0 for b in data["boundaries"])
        unit_ids = {u["unit_id"] for u in data["units"]}
        for boundary in data["boundaries"]:
            for key in ("unit_above", "unit_below"):
                assert boundary[key] == 0 or boundary[key] in unit_ids

        mazko = next(u for u in data["units"] if u["unit_name"] == "Mazko Formation")
        assert {l["name"] for l in mazko["lith"]} == {"sandstone", "siltstone"}
        assert mazko["b_int_name"] == "Ediacaran"
        assert mazko["b_age"] is not None, "modeled ages come from the age model"
        assert mazko["environ"][0]["name"] == "shoreface"

        assert _count(db, "units") == 0
        assert _count(db, "cols") == 0
        assert _count(db, "unit_boundaries") == 0

    def test_json_submission_is_ingested_like_the_workbook(
        self, db, test_project, default_age_model_ref, workbook_data
    ):
        result = ingest_column_data(db, workbook_data, dry_run=True)
        assert result["ok"] is True, result["notices"]
        assert len(result["data"]["units"]) == 6
        assert _count(db, "units") == 0


class TestNotices:
    def test_a_column_without_a_location_is_refused(
        self, db, test_project, default_age_model_ref, workbook_data
    ):
        for col in workbook_data["columns"]:
            if str(col["col_id"]) == "9999":
                col["lat"] = None
                col["lng"] = None
                col["geom"] = None
                col["rgeom"] = None

        dry = ingest_column_data(db, workbook_data, dry_run=True)
        assert dry["ok"] is False
        codes = {(n["code"], n.get("col_id")) for n in dry["notices"]}
        assert ("no-location", "9999") in codes
        assert dry["notice_counts"]["error"] >= 1
        # Checked but not written: the other columns still show
        assert dry["data"] is None or _count(db, "cols") == 0

        with raises(IngestValidationError) as err:
            ingest_column_data(db, workbook_data, dry_run=False)
        assert err.value.notices.has_errors
        assert _count(db, "cols") == 0

    def test_unknown_vocabulary_is_reported_not_fatal(
        self, db, test_project, default_age_model_ref, workbook_data
    ):
        units = workbook_data["units"]
        units[0]["environment"] = "underwater volcano lair"
        units[1]["lithology"] = "glorp"
        units[2]["b_int"] = "Age of Aquarius"

        result = ingest_column_data(db, workbook_data, dry_run=True)
        by_code = {}
        for notice in result["notices"]:
            by_code.setdefault(notice["code"], []).append(notice)

        assert "unknown-environment" in by_code
        assert by_code["unknown-environment"][0]["level"] == "warning"
        assert by_code["unknown-environment"][0]["row"] == 2
        assert "unknown-lithology" in by_code
        assert by_code["unknown-lithology"][0]["level"] == "warning"
        assert "unknown-interval" in by_code
        assert by_code["unknown-interval"][0]["level"] == "warning"
        assert by_code["unknown-interval"][0]["column"] == "b_int"
        # Unknown vocabulary is dropped with a warning; the column still ingests
        assert result["ok"] is True

    def test_contradictory_ages_are_an_error(
        self, db, test_project, default_age_model_ref, workbook_data
    ):
        unit = workbook_data["units"][0]
        unit["b_int"] = "Cretaceous"
        unit["t_int"] = "Cambrian"
        result = ingest_column_data(db, workbook_data, dry_run=True)
        codes = {n["code"]: n for n in result["notices"]}
        assert "contradictory-age-constraints" in codes
        assert codes["contradictory-age-constraints"]["level"] == "error"
        assert codes["contradictory-age-constraints"]["unit"] == "Test Formation"

    def test_a_column_without_ages_is_flagged(
        self, db, test_project, default_age_model_ref, workbook_data
    ):
        for unit in workbook_data["units"]:
            if str(unit["col_id"]) == "9999":
                for key in ("b_int", "t_int", "b_prop", "t_prop"):
                    unit[key] = None
        result = ingest_column_data(db, workbook_data, dry_run=True)
        notice = next(n for n in result["notices"] if n["code"] == "no-age-model")
        # A composite column is placed in time by its age model, so this is an error
        assert notice["level"] == "error"
        assert notice["col_id"] == "9999"


class TestCommit:
    def test_a_real_ingest_returns_the_written_data(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        result = ingest_columns_from_file(db, excel_file)
        assert result["dry_run"] is False
        assert result["ok"] is True
        assert result["summary"]["n_units"] == 6
        assert all(u["unit_id"] > 0 for u in result["data"]["units"])
        assert _count(db, "units") == 6


class TestPlacement:
    """A caller's placement overrides the file's project; see `Placement`."""

    @fixture(scope="class")
    def examples_project(self, db):
        db.run_query(
            "INSERT INTO macrostrat.projects (id, slug, project, descrip, timescale_id)"
            " VALUES (14, 'examples', 'Examples', 'Example columns', 11)"
        )
        db.session.commit()
        return 14

    def test_the_files_project_becomes_the_group(
        self, db, workbook_data, test_project, examples_project, default_age_model_ref
    ):
        placement = Placement(project=ProjectIdentifier(id=examples_project))
        result = ingest_column_data(
            db, workbook_data, dry_run=True, placement=placement
        )
        assert result["ok"], result["notices"]
        summary = result["summary"]
        assert summary["project"]["id"] == examples_project
        # Demoted, the workbook's own project name is the group's name.
        assert summary["col_group"] == workbook_data["metadata"]["project_name"]
        codes = {n["code"] for n in result["notices"]}
        assert "project-as-group" in codes

    def test_a_named_group_is_created_in_the_project(
        self, db, workbook_data, test_project, examples_project, default_age_model_ref
    ):
        placement = Placement(
            project=ProjectIdentifier(id=examples_project),
            col_group="Field season 2024",
        )
        result = ingest_column_data(
            db, workbook_data, dry_run=True, placement=placement
        )
        assert result["ok"], result["notices"]
        assert result["summary"]["col_group"] == "Field season 2024"

    def test_without_a_placement_the_file_decides(
        self, db, workbook_data, test_project, default_age_model_ref
    ):
        result = ingest_column_data(db, workbook_data, dry_run=True)
        assert result["ok"], result["notices"]
        assert result["summary"]["project"]["id"] == test_project
        assert result["summary"]["col_group"] == "Default"
