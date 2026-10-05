"""A lon/lat grid of lines noded into the topology (see `fixtures/05-grid.sql`)."""

import time

from rich import print

from .manager import NODING_TOLERANCE, RETRY_TOLERANCE, _duration

#: Line spacings in degrees, coarsest first; the index is the line's `level`.
#: A line belongs to the coarsest spacing that divides its coordinate, so no
#: two lines are collinear. Each line runs the whole way, pole to pole or
#: round the world: a face is split only when an edge closes a ring, so a line
#: noded in pieces splits nothing until its last piece, while a whole line
#: halves every region it crosses the moment it lands. Splitting a face costs
#: PostGIS time in proportion to the face's edges -- the ocean face had 43,000
#: on development -- so the coarse levels pay that a few times and the finer
#: ones split faces no larger than the previous level's cell.
#: Measured 2026-10-03 on local: the ocean face's busiest cell holds 5,754
#: edges at 5° against 33,482 for the whole face, at a cost of 2,592 faces.
GRID_LEVELS = (90, 30, 10, 5)

# Whole lines. The world rectangle's own lines (±180, ±90) are `global2`'s
# edges already and are left out.
_SEED = """
WITH lines AS (
  SELECT ST_MakeLine(ST_MakePoint(x, -90), ST_MakePoint(x, 90)) AS geometry
  FROM generate_series(-180 + :size, 180 - :size, :size) x
  WHERE NOT EXISTS (SELECT 1 FROM unnest(CAST(:coarser AS integer[])) c WHERE x % c = 0)
  UNION ALL
  SELECT ST_MakeLine(ST_MakePoint(-180, y), ST_MakePoint(180, y))
  FROM generate_series(-90 + :size, 90 - :size, :size) y
  WHERE NOT EXISTS (SELECT 1 FROM unnest(CAST(:coarser AS integer[])) c WHERE y % c = 0)
)
INSERT INTO map_bounds.grid_line (geometry, level)
SELECT ST_SetSRID(geometry, 4326), :level
FROM lines
WHERE CAST(:extent AS geometry) IS NULL
   OR ST_Intersects(ST_SetSRID(geometry, 4326), CAST(:extent AS geometry))
ON CONFLICT DO NOTHING
"""

_LEVELS = (
    "SELECT DISTINCT level FROM map_bounds.grid_line WHERE topo IS NULL ORDER BY level"
)

# A line split into pieces keeps its row and its error, prefixed `split:`, and
# is never pending again; its pieces are.
_PENDING = """
SELECT id, ST_Length(geometry) AS size FROM map_bounds.grid_line
WHERE topo IS NULL AND level = :level
  AND (topology_error IS NOT NULL) = :failed
  AND coalesce(topology_error, '') NOT LIKE 'split:%'
ORDER BY id
"""

_NODE = "SELECT map_bounds.node_grid_line(:id, CAST(:tolerance AS float8))"

# A line that fails at both tolerances is noded in cell-side pieces instead, so
# only the piece at the fault is lost.
_SPLIT = "SELECT map_bounds.split_grid_line(:id, CAST(:size AS float8))"

# The barrier rows of maps the lines split. The marks the lines left in the
# barrier layer are what `refresh_dirty_face_edge_relations` reads; they are
# removed afterwards so no later pass sees them.
_REBUILD = "SELECT map_bounds_topology.rebuild_dirty_edge_relations()"
_UNMARK = """
DELETE FROM map_bounds_topology.dirty_face WHERE map_layer = map_bounds.barrier_layer()
"""


def seed_grid(db, levels=GRID_LEVELS, *, extent=None) -> int:
    """Insert the grid's lines, one level per spacing; existing ones are kept.
    `extent`, a lon/lat (xmin, ymin, xmax, ymax), limits them to the lines
    crossing a region, so a grid can be built where it is needed first."""
    box = None
    if extent is not None:
        box = db.run_query(
            "SELECT ST_MakeEnvelope(:x0, :y0, :x1, :y1, 4326)",
            dict(zip(("x0", "y0", "x1", "y1"), extent)),
        ).scalar()
    n = 0
    for level, size in enumerate(levels):
        params = dict(size=size, level=level, extent=box, coarser=list(levels[:level]))
        n += db.run_query(_SEED, params).rowcount
    db.session.commit()
    return n


def node_grid(
    db, levels=GRID_LEVELS, *, tolerance: float = NODING_TOLERANCE
) -> tuple[int, int]:
    """Node every pending line, one per transaction, coarse levels first; then
    bring the maps' barrier rows up to date.

    Within a level, failures are retried at the reduced tolerance, and a line
    that still fails is split into pieces -- the level's own spacing, then each
    finer spacing in turn -- and the pieces tried, before the next level
    starts. A coarse line left out leaves a loop open, and every finer line
    inside it then splits the big face at full price; splitting down to the
    finest spacing confines the loss to one cell side at the fault."""
    noded = failed = 0
    t0 = time.time()

    def attempt(level):
        nonlocal noded, failed
        for retry, tol in ((False, tolerance), (True, RETRY_TOLERANCE)):
            pending = db.run_query(_PENDING, dict(level=level, failed=retry)).all()
            if retry and pending:
                print(f"  retrying {len(pending)} lines at tolerance {tol:g}")
            for i, line in enumerate(pending, start=1):
                t_line = time.time()
                ok = _node_line(db, line.id, tol)
                if ok:
                    noded += 1
                    if retry:
                        failed -= 1
                elif not retry:
                    failed += 1
                status = "[green]noded[/]" if ok else "[red]failed[/]"
                print(
                    f"  [dim]{i}/{len(pending)}[/] line {line.id} ({line.size:g}°) {status}"
                    f" in {time.time() - t_line:.1f} s [dim]({_duration(time.time() - t0)} total)[/]"
                )

    for level in db.run_query(_LEVELS).scalars().all():
        attempt(level)
        for size in levels[level:]:
            # Lines still failed and longer than this spacing: try them in pieces.
            whole = [
                l
                for l in db.run_query(_PENDING, dict(level=level, failed=True)).all()
                if l.size > size
            ]
            if not whole:
                continue
            print(f"  splitting {len(whole)} failed lines into {size:g}° pieces")
            for line in whole:
                db.run_query(_SPLIT, dict(id=line.id, size=size)).scalar()
                failed -= 1
            db.session.commit()
            attempt(level)
    if noded:
        db.run_query(_REBUILD).scalar()
        db.run_query(_UNMARK)
        db.session.commit()
    return noded, failed


def _node_line(db, line_id: int, tolerance: float) -> bool:
    """Node one line in its own transaction, recording a failure on it."""
    from sqlalchemy.exc import DBAPIError

    try:
        # Consume the result: an unread result keeps its connection's transaction
        # open, and the next call then waits on a second connection for ever.
        db.run_query(_NODE, dict(id=line_id, tolerance=tolerance)).scalar()
        db.session.commit()
        return True
    except DBAPIError as err:
        db.session.rollback()
        db.run_query(
            "UPDATE map_bounds.grid_line SET topology_error = :err WHERE id = :id",
            dict(id=line_id, err=str(err.orig).strip().splitlines()[0]),
        )
        db.session.commit()
        return False
