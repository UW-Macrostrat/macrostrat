from pytest import fixture

from macrostrat.core.defs_provider import MacrostratDataProvider
from macrostrat.utils import get_logger

from . import create_ignore_list
from .strat_names import _ignore_list, build_ignore_list

log = get_logger(__name__)


@fixture(autouse=True)
def lith_names_fixture(data_provider: MacrostratDataProvider):
    """Fixture to get a list of lithologies from a data provider available in this environment"""
    log.info(f"Getting lithologies from {data_provider}.")
    lithologies = data_provider.get_lithologies()

    lith_names = list(
        sorted({lithology.lith.lower() for lithology in lithologies if lithology.lith})
    )

    if not lith_names:
        raise RuntimeError(f"Could not get lith names from {data_provider}.")

    log.info(f"Found {len(lith_names)} lithologies in {data_provider}.")

    # Populate the ignore list used by tests

    assert len(lith_names) > 0
    create_ignore_list(lith_names)
    prev_val = _ignore_list.get()
    assert _ignore_list.get() is not None
    yield
    _ignore_list.set(prev_val)
