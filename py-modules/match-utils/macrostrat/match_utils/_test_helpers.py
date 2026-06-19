from functools import lru_cache
from urllib.parse import urljoin

from macrostrat.column_ingestion.defs_provider import (
    MacrostratAPIConfig,
    MacrostratAPIDataProvider,
)
from macrostrat.core.config import settings


def get_defs_api_base_url() -> str:
    base_url = getattr(settings, "base_url", None)

    if not base_url:
        env = getattr(settings, "env", None)
        raise RuntimeError(
            f"No base_url configured for Macrostrat environment {env!r}. "
            "Add base_url to macrostrat.toml for this environment."
        )

    return urljoin(base_url.rstrip("/") + "/", "api/v2")


@lru_cache(maxsize=1)
def get_test_lith_names():
    cfg = MacrostratAPIConfig(
        base_url=get_defs_api_base_url(),
        verify_ssl=getattr(settings, "api_ssl_verify", True),
    )
    provider = MacrostratAPIDataProvider(cfg)

    try:
        lithologies = provider.get_lithologies()
    finally:
        provider.close()

    lith_names = sorted(
        {lithology.lith.lower() for lithology in lithologies if lithology.lith}
    )

    if not lith_names:
        raise RuntimeError(
            f"No lithology names found from Macrostrat API at {cfg.base_url}"
        )

    return lith_names
