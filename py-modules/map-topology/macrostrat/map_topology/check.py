"""Where the topology's face labels have gone wrong, and whose edges bound them.

"Side-location conflict" is PostGIS finding an edge's two ends in different
faces where nothing separates them: the edges' face labels disagree with their
geometry. Nothing records the damage itself, but every failed noding names the
faces it met, so the errors on grid lines and map pieces are where to look.
"""

from dataclasses import dataclass

#: Faces named by noding failures, with how often and by what.
_SUSPECTS = r"""
WITH mentions AS (
  SELECT (regexp_matches(topology_error, 'face (\d+)', 'g'))[1]::int AS face_id,
         'grid' AS source
  FROM map_bounds.grid_line
  WHERE position('Side-location conflict' in topology_error) > 0
  UNION ALL
  SELECT (regexp_matches(topology_error, 'face (\d+)', 'g'))[1]::int, 'maps'
  FROM map_bounds.map_topo
  WHERE position('Side-location conflict' in topology_error) > 0
  UNION ALL
  SELECT unnest(CAST(:faces AS integer[])), 'given'
)
SELECT face_id, count(*) AS mentions, array_agg(DISTINCT source) AS sources
FROM mentions
GROUP BY face_id
ORDER BY count(*) DESC, face_id
"""

_FACE_DETAIL = """
SELECT f.face_id,
  ST_XMin(f.mbr) AS x0, ST_YMin(f.mbr) AS y0, ST_XMax(f.mbr) AS x1, ST_YMax(f.mbr) AS y1,
  (SELECT count(*) FROM map_bounds_topology.edge_data e
    WHERE e.left_face = f.face_id OR e.right_face = f.face_id) AS edges,
  (SELECT count(*) FROM map_bounds_topology.edge_data e
    JOIN map_bounds_topology.relation r
      ON r.element_type = 2 AND r.element_id = e.edge_id
     AND r.layer_id = map_bounds.grid_layer_id()
    WHERE e.left_face = f.face_id OR e.right_face = f.face_id) AS grid_edges,
  (SELECT array_agg(DISTINCT s.slug ORDER BY s.slug)
    FROM map_bounds_topology.edge_data e
    JOIN map_bounds_topology.__edge_relation er ON er.edge_id = e.edge_id
    JOIN maps.sources s ON s.source_id = er.line_id
    WHERE e.left_face = f.face_id OR e.right_face = f.face_id) AS maps
FROM map_bounds_topology.face f
WHERE f.face_id = ANY(:ids)
"""

#: Who an edge belongs to: the grid, the maps whose boundaries it carries, or
#: nothing (a primitive no longer used).
_OWNER = """coalesce(
  (SELECT 'grid' FROM map_bounds_topology.relation r
    WHERE r.element_type = 2 AND r.element_id = {edge}
      AND r.layer_id = map_bounds.grid_layer_id() LIMIT 1),
  (SELECT string_agg(DISTINCT s.slug, ', ')
    FROM map_bounds_topology.__edge_relation er
    JOIN maps.sources s ON s.source_id = er.line_id
    WHERE er.edge_id = {edge}),
  'no owner')"""

#: Errors in a box. Ring and edge errors name a signed edge, whose owner is
#: given; the others name a face or node.
_VALIDATE = f"""
SELECT v.error, v.id1,
  CASE WHEN position('edge' in v.error) > 0 OR position('ring' in v.error) > 0
    THEN {_OWNER.format(edge="abs(v.id1)")}
  END AS owner
FROM topology.ValidateTopology(
  'map_bounds_topology', ST_MakeEnvelope(:x0, :y0, :x1, :y1, 4326)
) v
"""

RING_ERROR = "mixed face labeling in ring"

#: A ring as PostGIS walks it, with the face each edge labels on the ring's
#: side: a ring follows an edge forwards with its face on the left, backwards
#: with it on the right.
_RING = """
WITH ring AS MATERIALIZED (
  SELECT r.sequence, r.edge,
    CASE WHEN r.edge > 0 THEN e.left_face ELSE e.right_face END AS face
  FROM topology.GetRingEdges('map_bounds_topology', :edge, :max_edges) r
  JOIN map_bounds_topology.edge_data e ON e.edge_id = abs(r.edge)
)
"""

_RING_LABELS = (
    _RING
    + """
SELECT x.face, count(*) AS n,
  EXISTS (SELECT 1 FROM map_bounds_topology.face f WHERE f.face_id = x.face) AS present
FROM ring x
GROUP BY x.face
ORDER BY count(*) DESC, x.face
"""
)

_RING_ODD_EDGES = (
    _RING
    + f"""
SELECT x.edge, x.face, {_OWNER.format(edge="abs(x.edge)")} AS owner
FROM ring x
WHERE x.face <> :majority
ORDER BY x.sequence
LIMIT :limit
"""
)

#: Longer than any ring a face of this topology has; a walk that exceeds it is
#: going round links that do not close.
_MAX_RING_EDGES = 200000


#: Validation is limited to faces no wider than this, in degrees, so that it
#: never runs over the ocean face or anything else continent-sized.
MAX_VALIDATE_SPAN = 5.0

#: Margin around a face's box, so the edges along its sides are inside.
_PAD = 0.01


@dataclass
class Suspect:
    face_id: int
    mentions: int
    sources: list[str]
    box: tuple[float, float, float, float] | None = None
    edges: int | None = None
    grid_edges: int | None = None
    maps: list[str] | None = None

    @property
    def present(self) -> bool:
        return self.box is not None or self.edges is not None

    @property
    def span(self) -> float | None:
        if self.box is None:
            return None
        x0, y0, x1, y1 = self.box
        return max(x1 - x0, y1 - y0)


def suspect_faces(db, faces: list[int] | None = None) -> list[Suspect]:
    """Faces named in noding failures, and any given, most-mentioned first."""
    rows = db.run_query(_SUSPECTS, dict(faces=faces or [])).all()
    suspects = [Suspect(r.face_id, r.mentions, list(r.sources)) for r in rows]
    by_id = {s.face_id: s for s in suspects}
    for r in db.run_query(_FACE_DETAIL, dict(ids=list(by_id))).all():
        s = by_id[r.face_id]
        if r.x0 is not None:
            s.box = (r.x0, r.y0, r.x1, r.y1)
        s.edges = r.edges
        s.grid_edges = r.grid_edges
        s.maps = list(r.maps or [])
    return suspects


def validate_box(db, box: tuple[float, float, float, float]) -> list:
    """`ValidateTopology` over a lon/lat box: each error, what it names, and the
    owner of that edge."""
    db.run_query("SET client_min_messages = warning")
    x0, y0, x1, y1 = box
    return db.run_query(_VALIDATE, dict(x0=x0, y0=y0, x1=x1, y1=y1)).all()


@dataclass
class Ring:
    edge: int
    #: (face, edges labelling it, whether the face exists), most labelled first.
    labels: list[tuple[int, int, bool]]
    #: (edge, face, owner) for edges disagreeing with the most-labelled face.
    odd: list[tuple[int, int, str]]
    error: str | None = None

    @property
    def length(self) -> int:
        return sum(n for _, n, _ in self.labels)


def walk_ring(db, edge: int, *, limit: int = 20) -> Ring:
    """Find the edges of a mislabelled ring that disagree with the rest.

    Every edge of a ring bounds the same face, so the face most of them label
    is the ring's, and the others are the labels in error -- the ones a repair
    would set to it.
    """
    from sqlalchemy.exc import DBAPIError

    params = dict(edge=edge, max_edges=_MAX_RING_EDGES)
    try:
        labels = db.run_query(_RING_LABELS, params).all()
        majority = labels[0].face
        odd = db.run_query(
            _RING_ODD_EDGES, dict(params, majority=majority, limit=limit)
        ).all()
    except DBAPIError as err:
        db.session.rollback()
        return Ring(edge, [], [], error=str(err.orig).strip().splitlines()[0])
    return Ring(
        edge,
        [(r.face, r.n, r.present) for r in labels],
        [(r.edge, r.face, r.owner) for r in odd],
    )


def padded(box: tuple[float, float, float, float]) -> tuple[float, ...]:
    x0, y0, x1, y1 = box
    return (x0 - _PAD, y0 - _PAD, x1 + _PAD, y1 + _PAD)
