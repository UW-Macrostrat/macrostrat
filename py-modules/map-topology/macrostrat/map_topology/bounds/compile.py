"""Compilation bounds: the `compile` opening operation, kept current by sync.

A compilation is not parted out and has no topogeometry. Its bounds are composed
like a map's, from an opening operation -- `compile`, the union of every noded
source below it, or `world` -- followed by whatever boundary operations were
authored. This module gives every compilation a `map_area` row and an opening
operation, recomputes `compile` where the members' bounds have changed, and
builds the result.
"""

from dataclasses import dataclass

from macrostrat.database import Database

from . import build as build_mod

#: A stamp over the noded sources below a compilation: which they are, and the
#: bounds each was noded from (`geometry_hash`, the library's stamp). The
#: `compile` opening reads their faces, so a source noded since, or re-noded from
#: new bounds, changes the stamp; one not yet noded is not in it.
_MEMBERS_HASH = """
SELECT md5(coalesce(string_agg(
    a.source_id || '/' || a.geometry_hash::text, ',' ORDER BY a.source_id
  ), ''))
FROM map_bounds.members_of(:source_id, true) m
JOIN map_bounds.map_area a ON a.source_id = m.source_id
WHERE a.topo IS NOT NULL AND a.geometry_hash IS NOT NULL
"""


@dataclass
class CompileResult:
    slug: str
    built: bool
    skipped: str | None = None
    error: str | None = None
    area_km: float | None = None


def compile_bounds(
    db: Database, *, force: bool = False, only: list[int] | None = None
) -> list[CompileResult]:
    """Give every compilation bounds, and refresh the stale ones.

    Mosaics are left alone: a mosaic's bounds are its own (it is parted out like
    a map). Every other compilation gets a `map_area` row and a `compile` opening
    operation if it has neither, and is rebuilt when the stamp over its members'
    bounds no longer matches the one recorded on the operation. `only` restricts
    the rebuild to those compilations; `force` rebuilds regardless of the stamp.
    """
    db.run_query(
        """
        INSERT INTO map_bounds.map_area (id, geometry, map_layer)
        SELECT DISTINCT cm.compilation_id,
               ST_GeomFromText('MULTIPOLYGON EMPTY', 4326),
               map_bounds.layer_id(s.scale)
        FROM map_bounds.compilation_member cm
        JOIN maps.sources s ON s.source_id = cm.compilation_id
        WHERE s.status_code = 'active'
          AND NOT map_bounds.is_mosaic(cm.compilation_id)
        ON CONFLICT (id) DO NOTHING
        """
    )
    db.run_query(
        """
        INSERT INTO map_bounds.boundary_op (source_id, position, operation)
        SELECT DISTINCT cm.compilation_id, 0, 'compile'
        FROM map_bounds.compilation_member cm
        JOIN map_bounds.map_area a ON a.source_id = cm.compilation_id
        WHERE NOT map_bounds.is_mosaic(cm.compilation_id)
          AND NOT EXISTS (
            SELECT 1 FROM map_bounds.boundary_op o
            WHERE o.source_id = cm.compilation_id AND o.position = 0
          )
        """
    )
    db.session.commit()

    rows = db.run_query(
        """
        SELECT o.id AS op_id, o.source_id, s.slug, o.operation,
               o.parameters->>'members_hash' AS recorded,
               o.geometry IS NULL AS empty
        FROM map_bounds.boundary_op o
        JOIN maps.sources s ON s.source_id = o.source_id
        WHERE o.position = 0
          AND map_bounds.is_compilation(o.source_id)
          AND NOT map_bounds.is_mosaic(o.source_id)
          AND (CAST(:only AS integer[]) IS NULL OR o.source_id = ANY(CAST(:only AS integer[])))
        ORDER BY s.slug
        """,
        dict(only=only),
    ).all()

    results = []
    for row in rows:
        if row.operation == "compile":
            current = db.run_query(
                _MEMBERS_HASH, dict(source_id=row.source_id)
            ).scalar()
            if not force and not row.empty and current == row.recorded:
                results.append(CompileResult(row.slug, built=False, skipped="current"))
                continue
            build_mod.recompute_opening(db, row.source_id)
            db.run_query(
                """
                UPDATE map_bounds.boundary_op
                SET parameters = parameters || jsonb_build_object('members_hash', :stamp::text)
                WHERE id = :id
                """,
                dict(id=row.op_id, stamp=current),
            )
            db.session.commit()
        elif not force and not _needs_build(db, row.source_id):
            results.append(CompileResult(row.slug, built=False, skipped="current"))
            continue

        res = build_mod.build(db, row.source_id)
        if res.error:
            results.append(CompileResult(row.slug, built=False, error=res.error))
            continue
        # The library's trigger cleared `geometry_hash` when the geometry changed;
        # a compilation is never noded, so stamp it complete here.
        db.run_query(
            """
            UPDATE map_bounds.map_area
            SET geometry_hash = md5(ST_AsBinary(geometry))::uuid
            WHERE source_id = :source_id
            """,
            dict(source_id=row.source_id),
        )
        db.session.commit()
        results.append(CompileResult(row.slug, built=True, area_km=res.area_km))
    return results


def _needs_build(db: Database, source_id: int) -> bool:
    """A `world` (or hand-opened) compilation is built once, then left alone."""
    return db.run_query(
        """
        SELECT ST_IsEmpty(a.geometry) OR a.geometry_hash IS NULL
        FROM map_bounds.map_area a WHERE a.source_id = :source_id
        """,
        dict(source_id=source_id),
    ).scalar()
