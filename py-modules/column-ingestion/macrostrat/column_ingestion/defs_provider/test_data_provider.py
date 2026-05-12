import pytest

from . import (
    MacrostratAPIDataProvider,
    MacrostratDatabaseDataProvider,
    MacrostratDataProvider,
    MacrostratMetadataPopulator,
)
from .models import Environment, Interval, Lithology, LithologyAttribute, Timescale


class StaticMacrostratDataProvider(MacrostratDataProvider):
    def _load_intervals(self) -> list[Interval]:
        return [
            Interval(
                id=1,
                age_bottom=66,
                age_top=0,
                interval_name="Cenozoic",
                interval_abbrev="Cz",
                interval_type="era",
                interval_color="#F2F91D",
                timescales=[
                    Timescale(
                        id=11,
                        timescale="international intervals",
                    ),
                    Timescale(
                        id=13,
                        timescale="international eras",
                    ),
                ],
            )
        ]

    def _load_lithologies(self) -> list[Lithology]:
        return [
            Lithology(
                id=1,
                lith="sandstone",
                lith_type="siliciclastic",
                lith_class="sedimentary",
                lith_fill=1,
                lith_color="#ffff00",
            )
        ]

    def _load_lithology_attributes(self) -> list[LithologyAttribute]:
        return [
            LithologyAttribute(
                id=1,
                lith_att="calcareous",
                att_type="lithology",
                lith_att_fill=1,
            )
        ]

    def _load_environments(self) -> list[Environment]:
        return [
            Environment(
                id=1,
                environ="marine",
                environ_type="",
                environ_class="marine",
                environ_color="#0000ff",
            )
        ]


@pytest.fixture
def static_provider():
    return StaticMacrostratDataProvider()


@pytest.fixture
def db_provider(env_db):
    return MacrostratDatabaseDataProvider(env_db)


@pytest.fixture
def api_provider():
    provider = MacrostratAPIDataProvider()
    try:
        yield provider
    finally:
        provider.close()


@pytest.fixture(
    params=[
        pytest.param("static_provider", id="static"),
        pytest.param("db_provider", id="database"),
        pytest.param("api_provider", id="api", marks=pytest.mark.web),
    ]
)
def provider(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize(
    ("method_name", "model_type"),
    [
        ("get_intervals", Interval),
        ("get_lithologies", Lithology),
        ("get_lithology_attributes", LithologyAttribute),
        ("get_environments", Environment),
    ],
)
def test_load_dataset(provider, method_name, model_type):
    values = getattr(provider, method_name)()

    assert len(values) > 0
    assert all(isinstance(value, model_type) for value in values)


def test_provider_caches_loaded_datasets(static_provider):
    first = static_provider.get_intervals()
    second = static_provider.get_intervals()

    assert first is second


def test_provider_cache_can_be_cleared(static_provider):
    first = static_provider.get_intervals()

    static_provider.clear_cache()
    second = static_provider.get_intervals()

    assert first == second
    assert first is not second


def test_populates_test_db(test_db):
    provider = StaticMacrostratDataProvider()

    MacrostratMetadataPopulator(provider, test_db).populate_all()

    interval = test_db.run_query(
        """
        SELECT
            id,
            age_bottom,
            age_top,
            interval_name,
            interval_abbrev,
            interval_type,
            interval_color
        FROM macrostrat.intervals
        WHERE id = 1
        """
    ).one()

    assert interval.id == 1
    assert interval.interval_name == "Cenozoic"
    assert interval.interval_abbrev == "Cz"
    assert interval.interval_type == "era"

    lithology = test_db.run_query(
        """
        SELECT
            id,
            lith,
            lith_type,
            lith_class,
            lith_fill,
            comp_coef,
            initial_porosity,
            bulk_density,
            lith_color
        FROM macrostrat.liths
        WHERE id = 1
        """
    ).one()

    assert lithology.id == 1
    assert lithology.lith == "sandstone"
    assert lithology.lith_type == "siliciclastic"
    assert lithology.lith_class == "sedimentary"

    lithology_attribute = test_db.run_query(
        """
        SELECT
            id,
            lith_att,
            att_type,
            lith_att_fill
        FROM macrostrat.lith_atts
        WHERE id = 1
        """
    ).one()

    assert lithology_attribute.id == 1
    assert lithology_attribute.lith_att == "calcareous"
    assert lithology_attribute.att_type == "lithology"

    environment = test_db.run_query(
        """
        SELECT
            id,
            environ,
            environ_type,
            environ_class,
            environ_color
        FROM macrostrat.environs
        WHERE id = 1
        """
    ).one()

    assert environment.id == 1
    assert environment.environ == "marine"
    assert environment.environ_type == ""
    assert environment.environ_class == "marine"

    timescale_links = test_db.run_query(
        """
        SELECT timescale_id, interval_id
        FROM macrostrat.timescales_intervals
        WHERE interval_id = 1
        ORDER BY timescale_id
        """
    ).fetchall()

    assert [(row.timescale_id, row.interval_id) for row in timescale_links] == [
        (11, 1),
        (13, 1),
    ]


def test_populator_is_idempotent(test_db):
    provider = StaticMacrostratDataProvider()
    populator = MacrostratMetadataPopulator(provider, test_db)

    populator.populate_all()
    populator.populate_all()

    assert (
        test_db.run_query(
            "SELECT count(*) FROM macrostrat.intervals WHERE id = 1"
        ).scalar()
        == 1
    )
    assert (
        test_db.run_query("SELECT count(*) FROM macrostrat.liths WHERE id = 1").scalar()
        == 1
    )
    assert (
        test_db.run_query(
            "SELECT count(*) FROM macrostrat.lith_atts WHERE id = 1"
        ).scalar()
        == 1
    )
    assert (
        test_db.run_query(
            "SELECT count(*) FROM macrostrat.environs WHERE id = 1"
        ).scalar()
        == 1
    )
    assert (
        test_db.run_query(
            """
            SELECT count(*)
            FROM macrostrat.timescales_intervals
            WHERE interval_id = 1
            """
        ).scalar()
        == 2
    )
