"""
Metadata provider for column ingestion. This gets common Macrostrat definitions, like
lithology, environments, intervals from a centralized source (either the database or API),
and caches them for testing etc.
"""

# https://macrostrat.org/api/v2/defs/intervals
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypeVar

from macrostrat.core.defs_provider import (
    MacrostratAPIConfig,
    MacrostratAPIDataProvider,
    MacrostratDataProvider,
    default_api_config,
)
from macrostrat.core.defs_provider_models import (
    Environment,
    Interval,
    Lithology,
    LithologyAttribute,
    Timescale,
)
from macrostrat.database import Database
from macrostrat.database.postgresql import OnConflictAction, upsert
from macrostrat.utils import get_logger

from ..database import get_macrostrat_table

log = get_logger(__name__)

T = TypeVar("T")


__here__ = Path(__file__).parent


def sql(name) -> str:
    return (__here__ / "sql" / f"{name}.sql").read_text()


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
            timescales = getattr(interval, "timescales", None)
            if timescales is None:
                timescales = []

            _interval = asdict(interval)
            # Don't need this, since we're using the linking table
            del _interval["timescales"]
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
            set_defaults(row, _defaults)
            yield row

    @list_builder
    def _prepare_lithology_attributes(self):
        _defaults = {
            "equiv": 0,
            "lith_att_fill": 0,
        }  # null values in lith_att_fill should be allowed
        for attribute in self.provider.get_lithology_attributes():
            row = asdict(attribute)
            # TODO: capture equivalence
            set_defaults(row, _defaults)
            yield row

    @list_builder
    def _prepare_environments(self):
        for environment in self.provider.get_environments():
            row = asdict(environment)
            set_defaults(row, {"environ_fill": 0})
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


def set_defaults(_dict, _defaults):
    for key, default in _defaults.items():
        if key not in _dict:
            _dict[key] = default
        if _dict[key] is None:
            _dict[key] = default
    return _dict
