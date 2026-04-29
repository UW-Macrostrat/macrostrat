"""
Metadata provider for column ingestion. This gets common Macrostrat definitions, like
lithology, environments, intervals from a centralized source (either the database or API),
and caches them for testing etc.
"""

# https://macrostrat.org/api/v2/defs/intervals

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Any, Callable, TypeVar

from httpx import Client
from macrostrat.database import Database
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import row

from ..database import get_macrostrat_table
from macrostrat.database.postgresql import upsert
from .models import (
    Interval,
    Lithology,
    LithologyAttribute,
    Environment,
)

T = TypeVar("T")


@dataclass
class MacrostratAPIConfig:
    base_url: str


default_api_config = MacrostratAPIConfig(base_url="https://macrostrat.org/api/v2")


class MacrostratDataProvider(ABC):
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
                    timescale["timescale_id"] for timescale in row.get("timescales", [])
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
                comp_coef=row.get("comp_coef"),
                initial_porosity=row.get("initial_porosity"),
                bulk_density=row.get("bulk_density"),
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


class MacrostratDatabaseDataProvider(MacrostratDataProvider):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    def _load_intervals(self) -> list[Interval]:
        rows = self.db.run_query(
            """
            SELECT
                i.id,
                i.age_bottom,
                i.age_top,
                i.interval_name,
                i.interval_abbrev,
                i.interval_type,
                i.interval_color,
                i.rank,
                array_remove(array_agg(ti.timescale_id), NULL) AS timescales
            FROM macrostrat.intervals i
            LEFT JOIN macrostrat.timescales_intervals ti
                ON i.id = ti.interval_id
            GROUP BY
                i.id,
                i.age_bottom,
                i.age_top,
                i.interval_name,
                i.interval_abbrev,
                i.interval_type,
                i.interval_color,
                i.rank
            ORDER BY i.age_top, i.age_bottom
            """
        ).fetchall()

        return [
            Interval(
                id=row.id,
                age_bottom=row.age_bottom,
                age_top=row.age_top,
                interval_name=row.interval_name,
                interval_abbrev=row.interval_abbrev,
                interval_type=row.interval_type,
                interval_color=row.interval_color,
                rank=row.rank,
                timescales=list(row.timescales or []),
            )
            for row in rows
        ]

    def _load_lithologies(self) -> list[Lithology]:
        rows = self.db.run_query(
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
            ORDER BY lith
            """
        ).fetchall()

        return [
            Lithology(
                id=row.id,
                lith=row.lith,
                lith_type=row.lith_type,
                lith_class=row.lith_class,
                lith_fill=row.lith_fill,
                comp_coef=row.comp_coef,
                initial_porosity=row.initial_porosity,
                bulk_density=row.bulk_density,
                lith_color=row.lith_color,
            )
            for row in rows
        ]

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
        ).fetchall()

        return [
            LithologyAttribute(
                id=row.id,
                lith_att=row.lith_att,
                att_type=row.att_type,
                lith_att_fill=row.lith_att_fill,
            )
            for row in rows
        ]

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
        ).fetchall()

        return [
            Environment(
                id=row.id,
                environ=row.environ,
                environ_type=row.environ_type,
                environ_class=row.environ_class,
                environ_color=row.environ_color,
            )
            for row in rows
        ]


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

    def _upsert(self, table_name: str, values: dict[str, Any], index_elements=("id",)):
        table = self._table(table_name)

        stmt = insert(table).values(**values)
        update_values = {
            column.name: getattr(stmt.excluded, column.name)
            for column in table.columns
            if column.name in values and column.name not in index_elements
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=list(index_elements),
            set_=update_values,
        )

        self.db.session.execute(stmt)

    def _insert_do_nothing(
        self,
        table_name: str,
        values: dict[str, Any],
        index_elements: tuple[str, ...] | None = None,
    ):
        table = self._table(table_name)

        stmt = insert(table).values(**values)
        if index_elements is None:
            stmt = stmt.on_conflict_do_nothing()
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=list(index_elements))

        self.db.session.execute(stmt)

    def populate_intervals(self):
        for interval in self.provider.get_intervals():
            values = asdict(interval)
            timescales = values.pop("timescales", [])

            table = self._table("intervals")

            stmt = upsert(table, values, ("id",)).returning(table.c.id)
            int_id = self.db.session.execute(stmt).scalar()

            for timescale in timescales:
                self.db.run_sql(
                    "INSERT INTO macrostrat.timescales_intervals (timescale_id, interval_id) VALUES (:timescale_id, :int_id) ON CONFLICT DO NOTHING",
                    {"timescale_id": timescale, "int_id": int_id},
                )

    # TODO: we set some values to NULLish when we should load them correctly in the future.

    def populate_lithologies(self):
        for lithology in self.provider.get_lithologies():
            # NOT NULL constraint on lithology.lith_equiv
            row = asdict(lithology)
            row.setdefault("lith_equiv", 0)
            self._upsert(
                "liths",
                row,
            )

    def populate_lithology_attributes(self):
        for attribute in self.provider.get_lithology_attributes():
            row = asdict(attribute)
            # TODO: capture equivalence
            row.setdefault("equiv", 0)
            self._upsert("lith_atts", row)

    def populate_environments(self):
        for environment in self.provider.get_environments():
            row = asdict(environment)
            row.setdefault("environ_fill", 0)
            self._upsert("environs", row)
