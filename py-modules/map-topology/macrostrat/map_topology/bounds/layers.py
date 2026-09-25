"""The registered compilations' bounds: the openings they are seeded with.

The layers are compilations like any other, but they exist before they have
members, so their bounds cannot wait for `topo update` to open them. The global
ones open with `world`; the scale layers open with `compile`, the union of the
sources below them. This is data, not schema: a fresh database gets it from
`create_topo_fixtures`, an existing one from the `compilation-layer-bounds`
migration, and the differ never carries it.
"""

from dataclasses import dataclass

from macrostrat.database import Database

#: Registered compilations whose bounds are the whole world, by assertion.
WORLD_LAYERS = ("tiny", "small", "carto-small", "carto-medium", "carto-large")

_WORLD = "ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))"


def seed_layer_openings(db: Database) -> tuple[int, int]:
    """Give every registered compilation a `map_area` row and an opening.

    Idempotent: rows that exist are left alone, including an opening someone
    has since changed by hand. Returns the number of areas and openings added.
    """
    areas = db.run_query(
        f"""
        INSERT INTO map_bounds.map_area (id, geometry, map_layer)
        SELECT ml.source_id,
          CASE WHEN ml.slug = ANY(:world) THEN {_WORLD}
               ELSE ST_GeomFromText('MULTIPOLYGON EMPTY', 4326) END,
          NULL
        FROM map_bounds.map_layer ml
        WHERE ml.source_id IS NOT NULL
        ON CONFLICT (id) DO NOTHING
        """,
        dict(world=list(WORLD_LAYERS)),
    ).rowcount
    # No ON CONFLICT: `boundary_op_unique_position` is deferrable, which ON
    # CONFLICT cannot use as an arbiter; the NOT EXISTS is the idempotence.
    openings = db.run_query(
        """
        INSERT INTO map_bounds.boundary_op (source_id, position, operation, note)
        SELECT ml.source_id, 0,
          CASE WHEN ml.slug = ANY(:world) THEN 'world' ELSE 'compile' END,
          'Seeded with the compilation schema'
        FROM map_bounds.map_layer ml
        WHERE ml.source_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.boundary_op o
            WHERE o.source_id = ml.source_id AND o.position = 0
          )
        """,
        dict(world=list(WORLD_LAYERS)),
    ).rowcount
    return areas, openings


@dataclass
class LayerBounds:
    source_id: int
    slug: str
    has_area: bool
    opening: str | None
    cached: bool
    built: bool

    @property
    def complete(self) -> bool:
        return self.has_area and self.opening is not None and self.cached and self.built


def layer_bounds(db: Database) -> list[LayerBounds]:
    """Where each registered compilation's bounds stand."""
    rows = db.run_query(
        """
        SELECT ml.source_id, ml.slug,
               a.source_id IS NOT NULL AS has_area,
               o.operation AS opening,
               o.geometry IS NOT NULL AS cached,
               a.geometry IS NOT NULL AND NOT ST_IsEmpty(a.geometry)
                 AND a.geometry_hash IS NOT NULL AS built
        FROM map_bounds.map_layer ml
        LEFT JOIN map_bounds.map_area a ON a.source_id = ml.source_id
        LEFT JOIN map_bounds.boundary_op o
          ON o.source_id = ml.source_id AND o.position = 0
        WHERE ml.source_id IS NOT NULL
        ORDER BY ml.id
        """
    ).all()
    return [LayerBounds(**dict(r._mapping)) for r in rows]
