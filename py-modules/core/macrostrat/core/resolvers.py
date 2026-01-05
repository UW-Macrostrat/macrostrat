from os import environ
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


# Source roots for application components
# This is primarily used to set up a locally running (Docker compose) version of the application stack
class _SourceRootConfig(BaseModel):
    api: Optional[Path] = None
    api_v3: Optional[Path] = None
    tileserver: Optional[Path] = None
    corelle: Optional[Path] = None
    web: Optional[Path] = None
    map_cache: Optional[Path] = None


def cast_sources(value):
    def get_source(key: str) -> Optional[Path]:
        if value is None:
            return None
        src = getattr(value, key, None)
        if src is not None:
            return Path(src)
        return None

    return _SourceRootConfig(
        api=get_source("api"),
        api_v3=get_source("api_v3"),
        tileserver=get_source("tileserver"),
        corelle=get_source("corelle"),
        web=get_source("web"),
        map_cache=get_source("map_cache"),
    )


def setup_source_roots_environment(sources: _SourceRootConfig):
    for k, v in sources.model_dump().items():
        if v is not None:
            environ[f"MACROSTRAT_{k.upper()}_SRC"] = str(v)
