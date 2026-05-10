"""
Metadata provider for column ingestion. This gets common Macrostrat definitions, like
lithology, environments, intervals from a centralized source (either the database or API),
and caches them for testing etc.
"""

# https://macrostrat.org/api/v2/defs/intervals

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Callable, TypeVar, Generator
from pathlib import Path

from httpx import Client
from macrostrat.database import Database
from macrostrat.database.postgresql import upsert, OnConflictAction
from macrostrat.utils import get_logger

from ..database import get_macrostrat_table
from .models import (
    Interval,
    Lithology,
    LithologyAttribute,
    Environment,
    Timescale,
)

log = get_logger(__name__)

T = TypeVar("T")


__here__ = Path(__file__).parent


def sql(name) -> str:
    return (__here__ / "sql" / f"{name}.sql").read_text()


@dataclass
class MacrostratAPIConfig:
    base_url: str


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
        self.client = Client(base_url=config.base_url)

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


def list_builder(fn):
    """Decorator that converts a function that returns an iterable into one that returns a list"""

    def wrapper(*args, **kwargs):
        return list(fn(*args, **kwargs))

    return wrapper


class MacrostratDatabaseDataProvider(MacrostratDataProvider):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    @list_builder
    def _load_intervals(self):
        rows = self.db.run_query(sql("load-intervals")).mappings()
        for row in rows:
            res = dict(row)
            timescales = row.get("timescales")
            if timescales is not None:
                timescales = [Timescale(v["id"], v["name"]) for v in timescales]
            res["timescales"] = timescales

            yield Interval(**res)

    def _load_lithologies(self) -> list[Lithology]:
        rows = self.db.run_query(
            """
            SELECT
                id,
                lith,
                lith_type,
                lith_class,
                lith_fill,
                lith_color
            FROM macrostrat.liths
            ORDER BY lith
            """
        ).mappings()

        return [Lithology(**row) for row in rows]

    def _load_lithology_attributes(self) -> list[LithologyAttribute]:
        rows = self.db.run_query(
            """
            SELECT
                id,
                lith_att,
                att_type,
                lith_att_fill
            FROM macrostrat.lith_atts
            ORDER BY lith_att
            """
        ).mappings()

        return [LithologyAttribute(**row) for row in rows]

    def _load_environments(self) -> list[Environment]:
        rows = self.db.run_query(
            """
            SELECT
                id,
                environ,
                environ_type,
                environ_class,
                environ_color
            FROM macrostrat.environs
            ORDER BY environ
            """
        ).mappings()

        return [Environment(**row) for row in rows]


class MacrostratMetadataPopulator:
    def __init__(
        self,
        provider: MacrostratDataProvider,
        db: Database,
    ):
        self.provider = provider
        self.db = db

    def populate_all(self):
        self.populate_intervals()
        self.populate_lithologies()
        self.populate_lithology_attributes()
        self.populate_environments()

    def _table(self, table_name: str):
        return get_macrostrat_table(self.db, table_name)

    def _upsert(self, table_name: str, values: dict[str, Any], index_elements=None):
        table = self._table(table_name)

        stmt = upsert(table, values, index_elements=index_elements)
        self.db.session.execute(stmt)
        self.db.session.commit()

    def _insert_do_nothing(
        self,
        table_name: str,
        values: dict[str, Any],
        index_elements: tuple[str, ...] | None = None,
    ):
        table = self._table(table_name)
        stmt = upsert(table, values, index_elements=index_elements)
        self.db.session.execute(stmt)

    def populate_intervals(self):
        timescales_table = self._table("timescales")
        intervals_table = self._table("intervals")

        _timescales = set()
        _intervals = []
        _timescale_intervals = []

        for interval in self.provider.get_intervals():
            timescales = getattr(interval, "timescales", [])

            _interval = asdict(interval)
            del _interval[
                "timescales"
            ]  # Don't need this, since we're using the linking table
            _intervals.append(_interval)
            for timescale in timescales:
                _timescales.add(timescale)
                _timescale_intervals.append(
                    {"timescale_id": timescale.id, "interval_id": interval.id}
                )

        _timescales = [asdict(timescale) for timescale in _timescales]

        # Do inserts
        # First, add timescales
        queries = [
            upsert(timescales_table, _timescales),
            upsert(
                intervals_table,
                _intervals,
                on_conflict=OnConflictAction.DO_NOTHING,
            ),
        ]
        for query in queries:
            self.db.session.execute(query)
        # For conflicted values, nothing is returned
        # int_id = res.scalar() or interval.id

        self.db.run_query(
            "INSERT INTO macrostrat.timescales_intervals (timescale_id, interval_id) VALUES (:timescale_id, :interval_id) ON CONFLICT DO NOTHING",
            _timescale_intervals,
            use_instance_params=False,
        )

    @list_builder
    def _prepare_lithologies(self):
        _defaults = {
            "lith_equiv": 0,
            "comp_coef": 0,
            "initial_porosity": 0,
            "bulk_density": 0,
        }
        for lithology in self.provider.get_lithologies():
            # Don't include material properties and bulk information (for now)
            row = asdict(lithology)
            for k, v in _defaults.items():
                row.setdefault(k, v)
            yield row

    @list_builder
    def _prepare_lithology_attributes(self):
        for attribute in self.provider.get_lithology_attributes():
            row = asdict(attribute)
            # TODO: capture equivalence
            row.setdefault("equiv", 0)
            yield row

    @list_builder
    def _prepare_environments(self):
        for environment in self.provider.get_environments():
            row = asdict(environment)
            row.setdefault("environ_fill", 0)
            yield row

    def populate_lithologies(self):
        self._upsert(
            "liths",
            self._prepare_lithologies(),
        )

    def populate_lithology_attributes(self):
        self._upsert("lith_atts", self._prepare_lithology_attributes())

    def populate_environments(self):
        self._upsert("environs", self._prepare_environments())
