"""Schema chunks apply by environment class, on the same scale the gates use."""

from pathlib import Path

from pytest import mark, raises

from macrostrat.core.environment import EnvironmentClass, classes_up_to
from macrostrat.core.schema_definition import SchemaDefinition


class TestClassLadder:
    def test_rank_orders_the_scale(self):
        ranks = [c.rank for c in EnvironmentClass]
        assert ranks == sorted(ranks)
        assert EnvironmentClass.Local.rank < EnvironmentClass.Production.rank

    @mark.parametrize(
        "top,expected",
        [
            ("local", {"local"}),
            ("development", {"local", "development"}),
            ("staging", {"local", "development", "staging"}),
            ("production", {"local", "development", "staging", "production"}),
        ],
    )
    def test_classes_up_to(self, top, expected):
        assert {c.value for c in classes_up_to(top)} == expected


class TestChunkApplicability:
    def test_everywhere_when_unspecified(self):
        chunk = SchemaDefinition(name="x")
        assert all(chunk.applies_to(c) for c in EnvironmentClass)

    def test_class_names_are_normalised(self):
        chunk = SchemaDefinition(
            name="dev", environments=frozenset({"development", "local"})
        )
        assert chunk.environments == classes_up_to(EnvironmentClass.Development)
        assert chunk.applies_to(EnvironmentClass.Local)
        assert chunk.applies_to("development")
        assert not chunk.applies_to("staging")
        assert not chunk.applies_to(EnvironmentClass.Production)

    def test_an_environment_name_is_not_a_class(self):
        """`local-ingestion` says nothing about where it sits; resolve first."""
        chunk = SchemaDefinition(name="dev", environments={"local"})
        with raises(ValueError):
            chunk.applies_to("local-ingestion")

    def test_unknown_class_in_declaration_is_rejected(self):
        with raises(ValueError):
            SchemaDefinition(name="x", environments={"laptop"})
