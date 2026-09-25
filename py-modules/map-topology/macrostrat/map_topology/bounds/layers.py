"""The registered compilations' bounds: the openings they are seeded with.

The layers are compilations like any other, but they exist before they have
members, so their bounds cannot wait for `topo update` to open them. The global
ones open with `world`; the scale layers open with `compile`, the union of the
sources below them. Multiscale compilations (`carto`, `carto-v1`) are global by
definition and open with `world` too. This is data, not schema: a fresh
database gets it from `create_topo_fixtures`, an existing one from the
`compilation-layer-bounds` and `compilation-multiscale` migrations, and the
differ never carries it.
"""

from dataclasses import dataclass

from macrostrat.database import Database

#: Registered compilations whose bounds are the whole world, by assertion.
WORLD_LAYERS = ("tiny", "small", "carto-small", "carto-medium", "carto-large")

_WORLD = "ST_Multi(ST_MakeEnvelope(-180, -90, 180, 90, 4326))"

#: The compilations seeded here: the registered layers, plus every multiscale
#: compilation, which has no `map_layer` row (it solves no faces) but bounds
#: all the same. `sort_key` keeps the layers in register order, ahead of the rest.
_SEEDED = """
SELECT ml.source_id, ml.slug, ml.id AS sort_key, false AS is_multiscale
FROM map_bounds.map_layer ml
WHERE ml.source_id IS NOT NULL
UNION ALL
SELECT c.source_id, s.slug, 1000000 + c.source_id, true
FROM map_bounds.compilation c
JOIN maps.sources s ON s.source_id = c.source_id
WHERE c.assembly_mode = 'multiscale'
"""


def seed_layer_openings(db: Database) -> tuple[int, int]:
    """Give every registered compilation a `map_area` row and an opening.

    Idempotent: rows that exist are left alone, including an opening someone
    has since changed by hand. Returns the number of areas and openings added.
    """
    areas = db.run_query(
        f"""
        INSERT INTO map_bounds.map_area (id, geometry, map_layer)
        SELECT r.source_id,
          CASE WHEN r.slug = ANY(:world) OR r.is_multiscale THEN {_WORLD}
               ELSE ST_GeomFromText('MULTIPOLYGON EMPTY', 4326) END,
          NULL
        FROM ({_SEEDED}) r
        ON CONFLICT (id) DO NOTHING
        """,
        dict(world=list(WORLD_LAYERS)),
    ).rowcount
    # No ON CONFLICT: `boundary_op_unique_position` is deferrable, which ON
    # CONFLICT cannot use as an arbiter; the NOT EXISTS is the idempotence.
    openings = db.run_query(
        f"""
        INSERT INTO map_bounds.boundary_op (source_id, position, operation, note)
        SELECT r.source_id, 0,
          CASE WHEN r.slug = ANY(:world) OR r.is_multiscale THEN 'world'
               ELSE 'compile' END,
          'Seeded with the compilation schema'
        FROM ({_SEEDED}) r
        WHERE NOT EXISTS (
            SELECT 1 FROM map_bounds.boundary_op o
            WHERE o.source_id = r.source_id AND o.position = 0
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
    has_members: bool
    is_multiscale: bool = False

    @property
    def complete(self) -> bool:
        """Seeded and built, where there is something to build: a `compile`
        layer with no members yet has empty bounds and is complete as it is."""
        if not (self.has_area and self.opening is not None and self.cached):
            return False
        if self.opening == "compile" and not self.has_members:
            return True
        return self.built


def layer_bounds(db: Database) -> list[LayerBounds]:
    """Where each registered compilation's bounds stand."""
    rows = db.run_query(
        f"""
        SELECT r.source_id, r.slug,
               a.source_id IS NOT NULL AS has_area,
               o.operation AS opening,
               o.geometry IS NOT NULL AS cached,
               a.geometry IS NOT NULL AND NOT ST_IsEmpty(a.geometry)
                 AND a.geometry_hash IS NOT NULL AS built,
               map_bounds.is_compilation(r.source_id) AS has_members,
               r.is_multiscale
        FROM ({_SEEDED}) r
        LEFT JOIN map_bounds.map_area a ON a.source_id = r.source_id
        LEFT JOIN map_bounds.boundary_op o
          ON o.source_id = r.source_id AND o.position = 0
        ORDER BY r.sort_key
        """
    ).all()
    return [LayerBounds(**dict(r._mapping)) for r in rows]
