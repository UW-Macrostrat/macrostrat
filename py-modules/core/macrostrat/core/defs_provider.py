from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from httpx import Client

from .defs_provider_models import (
    Environment,
    Interval,
    Lithology,
    LithologyAttribute,
    Timescale,
)

T = TypeVar("T")


@dataclass
class MacrostratAPIConfig:
    base_url: str
    verify_ssl: bool = True


default_api_config = MacrostratAPIConfig(base_url="https://macrostrat.org/api/v2")

class MacrostratDataProvider(ABC):
    """
    Provides an abstract interface for accessing Macrostrat data.

    This class serves as a blueprint for implementing data providers that handle
    the retrieval and caching of geological data, specifically intervals,
    lithologies, lithology attributes, and environments. Subclasses are required
    to implement the abstract methods to define the data loading logic.

    :ivar intervals: Cached list of geological intervals.
    :type intervals: list[Interval] | None
    :ivar lithologies: Cached list of lithologies.
    :type lithologies: list[Lithology] | None
    :ivar lithology_attributes: Cached list of lithology attributes.
    :type lithology_attributes: list[LithologyAttribute] | None
    :ivar environments: Cached list of environments.
    :type environments: list[Environment] | None
    """

    def __init__(self):
        self._intervals: list[Interval] | None = None
        self._lithologies: list[Lithology] | None = None
        self._lithology_attributes: list[LithologyAttribute] | None = None
        self._environments: list[Environment] | None = None

    def clear_cache(self):
        self._intervals = None
        self._lithologies = None
        self._lithology_attributes = None
        self._environments = None

    def _cached(self, key: str, loader: Callable[[], list[T]]) -> list[T]:
        value = getattr(self, key)
        if value is None:
            value = loader()
            setattr(self, key, value)
        return value

    def get_intervals(self) -> list[Interval]:
        return self._cached("_intervals", self._load_intervals)

    def get_lithologies(self) -> list[Lithology]:
        return self._cached("_lithologies", self._load_lithologies)

    def get_lithology_attributes(self) -> list[LithologyAttribute]:
        return self._cached(
            "_lithology_attributes",
            self._load_lithology_attributes,
        )

    def get_environments(self) -> list[Environment]:
        return self._cached("_environments", self._load_environments)

    @abstractmethod
    def _load_intervals(self) -> list[Interval]:
        pass

    @abstractmethod
    def _load_lithologies(self) -> list[Lithology]:
        pass

    @abstractmethod
    def _load_lithology_attributes(self) -> list[LithologyAttribute]:
        pass

    @abstractmethod
    def _load_environments(self) -> list[Environment]:
        pass


class MacrostratAPIDataProvider(MacrostratDataProvider):
    def __init__(self, config: MacrostratAPIConfig = default_api_config):
        super().__init__()
        self.config = config
        self.client = Client(base_url=config.base_url, verify=config.verify_ssl)

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _get_all(self, route: str) -> list[dict[str, Any]]:
        response = self.client.get(route, params={"all": ""})
        response.raise_for_status()

        payload = response.json()
        return payload["success"]["data"]

    def _load_intervals(self) -> list[Interval]:
        rows = self._get_all("/defs/intervals")

        return [
            Interval(
                id=row["int_id"],
                age_bottom=row.get("b_age"),
                age_top=row.get("t_age"),
                interval_name=row.get("name"),
                interval_abbrev=row.get("abbrev"),
                interval_type=row.get("int_type"),
                interval_color=row.get("color"),
                timescales=[
                    Timescale(timescale["timescale_id"], timescale["name"])
                    for timescale in row.get("timescales", [])
                    if timescale["timescale_id"] is not None
                ],
            )
            for row in rows
        ]

    def _load_lithologies(self) -> list[Lithology]:
        rows = self._get_all("/defs/lithologies")

        return [
            Lithology(
                id=row["lith_id"],
                lith=row.get("name"),
                lith_type=row.get("type"),
                lith_class=row.get("class"),
                lith_fill=row.get("fill"),
                lith_color=row.get("color"),
            )
            for row in rows
        ]

    def _load_lithology_attributes(self) -> list[LithologyAttribute]:
        rows = self._get_all("/defs/lithology_attributes")

        return [
            LithologyAttribute(
                id=row["lith_att_id"],
                lith_att=row.get("name"),
                att_type=row.get("type"),
                lith_att_fill=row.get("fill"),
            )
            for row in rows
        ]

    def _load_environments(self) -> list[Environment]:
        rows = self._get_all("/defs/environments")

        return [
            Environment(
                id=row["environ_id"],
                environ=row.get("name"),
                environ_type=row.get("type"),
                environ_class=row.get("class"),
                environ_color=row.get("color"),
            )
            for row in rows
        ]

