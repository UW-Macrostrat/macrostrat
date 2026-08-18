"""Tests for `unit_environs` and `unit_notes`."""

from pytest import raises

from macrostrat.column_ingestion.environs import (
    EnvironsProcessor,
    UnknownEnvironError,
    split_environments,
)
from macrostrat.column_ingestion.ingest import ingest_columns_from_file
from macrostrat.column_ingestion.units import compose_note

# --- pure -------------------------------------------------------------------------


def test_environments_split_on_semicolons():
    assert split_environments("marine; shoreface") == ["marine", "shoreface"]
    assert split_environments("marine") == ["marine"]
    assert split_environments(None) == []
    assert split_environments("  ") == []


def test_note_is_composed_from_description_and_comments():
    assert compose_note("A description", "A comment") == "A description; A comment"


def test_note_uses_whichever_field_is_present():
    assert compose_note("A description", None) == "A description"
    assert compose_note(None, "A comment") == "A comment"
    assert compose_note("A description", "   ") == "A description"


def test_no_note_when_there_is_nothing_to_say():
    """`None` means no row is written at all, rather than an empty note."""
    assert compose_note(None, None) is None
    assert compose_note("", "  ") is None


# --- resolving environments against the lookup table ------------------------------


class TestEnvironsProcessor:
    def test_match_by_name_case_insensitively(self, db):
        processor = EnvironsProcessor(db)

        assert processor.match("shoreface").name == "shoreface"
        assert processor.match("SHOREFACE").id == processor.match("shoreface").id

    def test_match_by_id(self, db):
        processor = EnvironsProcessor(db)
        by_name = processor.match("shoreface")

        assert processor.match(str(by_name.id)) == by_name

    def test_marine_and_non_marine_resolve_to_environments_not_classes(self, db):
        """`marine` and `non-marine` are rows in `environs` (ids 38 and 88) that happen to
        share a name with their own `environ_class`. A token must resolve to the row."""
        processor = EnvironsProcessor(db)

        assert processor.match("marine").id == 38
        assert processor.match("non-marine").id == 88

    def test_environ_type_values_are_not_match_targets(self, db):
        """No `environ_type` exists as an environment name, so `carbonate` and friends
        match nothing rather than silently resolving to a category."""
        processor = EnvironsProcessor(db)

        for environ_type in ("carbonate", "siliciclastic", "fluvial", "glacial"):
            assert processor.match(environ_type) is None, environ_type

        with raises(UnknownEnvironError):
            processor("carbonate")

    def test_multiple_entries_resolve_to_a_set(self, db):
        processor = EnvironsProcessor(db)

        assert {e.name for e in processor("marine; shoreface")} == {
            "marine",
            "shoreface",
        }

    def test_unknown_environments_are_reported_not_dropped(self, db):
        """Environment vocabulary is a controlled list, so an unmatched token is far more
        likely a typo than something to pattern-match past."""
        processor = EnvironsProcessor(db)

        with raises(UnknownEnvironError) as err:
            processor("marine; nonsense-value")

        assert "nonsense-value" in str(err.value)

    def test_empty_environment_is_not_an_error(self, db):
        """Two of the fixture's six units leave `environment` blank."""
        assert EnvironsProcessor(db)(None) == set()


# --- the whole path --------------------------------------------------------------


class TestIngestedEnvironsAndNotes:
    def test_environments_are_written(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        """Four of the six fixture units name an environment; two leave it blank."""
        ingest_columns_from_file(db, excel_file)

        rows = db.run_query(
            """
            SELECT u.strat_name, e.environ, ue.ref_id
            FROM macrostrat.unit_environs ue
            JOIN macrostrat.units u ON u.id = ue.unit_id
            JOIN macrostrat.environs e ON e.id = ue.environ_id
            ORDER BY u.strat_name
            """
        ).fetchall()

        assert {r.environ for r in rows} == {"non-marine", "marine", "shoreface"}
        assert len(rows) == 4, "units with a blank environment get no row"
        # The column default is 1, which is not a valid reference in a fresh database.
        assert all(r.ref_id is None for r in rows)

    def test_notes_are_written_and_composed(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)

        notes = dict(
            db.run_query(
                """
                SELECT u.strat_name, n.notes
                FROM macrostrat.unit_notes n
                JOIN macrostrat.units u ON u.id = n.unit_id
                """
            ).fetchall()
        )

        # 'Test Formation' has a description only.
        assert notes["Test Formation"] == "Very cool unit"
        # 'Mazko Formation' has both, joined.
        assert notes["Mazko Formation"] == (
            "another cool unit; I'm not sure I like the lithology convention."
        )
        # Units with neither get no row at all.
        assert "unnamed granite" not in notes

    def test_environs_and_notes_survive_a_reimport(
        self, db, test_project, default_age_model_ref, excel_file
    ):
        ingest_columns_from_file(db, excel_file)

        def snapshot():
            return {
                table: [
                    r[0]
                    for r in db.run_query(
                        f"SELECT id FROM macrostrat.{table} ORDER BY id"
                    ).fetchall()
                ]
                for table in ("unit_environs", "unit_notes")
            }

        first = snapshot()
        assert first["unit_environs"] and first["unit_notes"]

        ingest_columns_from_file(db, excel_file)

        assert snapshot() == first, "no churn and no accumulation on a second import"
