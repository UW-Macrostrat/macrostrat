import pytest
from dotenv import load_dotenv

load_dotenv()

from macrostrat_tileserver.tests.fixtures import app, client, db  # noqa


def pytest_addoption(parser):
    parser.addoption(
        "--skip-legacy-raster", action="store_true", help="Skip legacy raster tests"
    )
    parser.addoption(
        "--no-drop",
        action="store_true",
        default=False,
        help="Keep the database after tests",
    )


def pytest_configure(config):
    # register an additional marker
    # This is kind of an annoying way to specify this
    config.addinivalue_line(
        "markers", "legacy_raster: mark test as legacy raster test."
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-legacy-raster"):
        # --runslow given in cli: do not skip slow tests
        skip_slow = pytest.mark.skip(reason="--skip-legacy-raster option provided")
        for item in items:
            if "legacy_raster" in item.keywords:
                item.add_marker(skip_slow)
