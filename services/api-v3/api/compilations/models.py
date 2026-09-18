"""Response models for the compilation graph.

The vocabulary is the database's, not a second one invented here: a compilation
is a map with members, a served layer is a compilation with a `map_layer` row,
and materialization is a lifecycle state rather than a kind. The flags below are
the ones a client needs to tell those cases apart, and they are derived in SQL so
this module stays a description of the payload.
"""

from typing import Literal, Optional

from pydantic import BaseModel

CompilationState = Literal["virtual", "current", "stale", "ingested"]
CompilationContent = Literal["ingested", "derived"]


class MapNode(BaseModel):
    """Facts shared by every node of the graph, compilation or ordinary map."""

    source_id: int
    slug: str
    name: Optional[str] = None
    scale: Optional[str] = None

    #: A compilation served as a tile layer -- `medium`, `carto-large`. Layers
    #: are structural: nobody means to *see* one, so a client usually renders
    #: them as containers rather than as maps.
    is_served_layer: bool = False
    #: Has members.
    is_compilation: bool = False
    #: Holds polygons of its own, and is therefore where identity resolution
    #: stops. True for any ingested map; true for a compilation only once it has
    #: been materialized.
    holds_polygons: bool = False
    #: A compilation that *replaced* its constituents. This is the distinction a
    #: UI wants to call out -- `holds_polygons` alone is true of every ordinary
    #: map too.
    is_materialized: bool = False
    #: A member of a mosaic: a real source with a citation and a footprint that
    #: *is* its extent, whose content is the mosaic's content inside it. No
    #: polygons, linework or faces of its own. SGMC's published maps are the case.
    is_mosaic_member: bool = False

    n_members: int = 0
    #: Where a materialized compilation's polygons came from: `derived` from its
    #: members (and reversible), or `ingested` with the compilation itself (in
    #: which case the members are provenance, not material).
    content: Optional[CompilationContent] = None
    area_km: Optional[float] = None
    #: In no compilation at all — an ingested map nothing has wrapped yet. Not a
    #: kind; just a state of the catalog, and one worth showing rather than
    #: silently omitting.
    is_standalone: bool = False
    #: Stage I supersession: the map that replaced this one. Often the reason a
    #: map sits outside every compilation.
    superseded_by: Optional[int] = None


class CompilationFacts(MapNode):
    """A compilation's own state, shared by the index and the detail view."""

    map_layer: Optional[int] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None

    #: Every map the compilation resolves to, descending through member
    #: compilations to the maps at the bottom.
    n_sources: int = 0
    assembly_mode: Optional[str] = None
    state: Optional[CompilationState] = None


class CompilationSummary(CompilationFacts):
    """A node of the compilation graph, as returned by the index."""

    #: The compilations that claim this one. Empty makes it a root of the graph.
    #: More than one is normal -- `medium` sits under both carto layers -- so
    #: this is a DAG that a client renders as a tree by repeating shared nodes.
    parent_ids: list[int] = []


class MemberRef(MapNode):
    """A map as seen from the compilation that contains it."""

    #: Higher wins where members overlap; null in a disjoint mosaic, where
    #: nothing overlaps and the ordering carries no meaning.
    priority: Optional[int] = None
    role: Optional[str] = None
    state: Optional[CompilationState] = None


class ParentRef(BaseModel):
    source_id: int
    slug: str
    name: Optional[str] = None
    priority: Optional[int] = None
    role: Optional[str] = None
    is_served_layer: bool = False


class CompilationDetail(CompilationFacts):
    """One node with the edges on either side of it."""

    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    url: Optional[str] = None
    status_code: Optional[str] = None
    is_finalized: bool = False
    layer_description: Optional[str] = None
    note: Optional[str] = None

    #: The layer whose faces represent this map. Null for a served layer, which
    #: *is* one, and for a map that is not in the topology.
    placed_in_layer: Optional[int] = None

    #: The member set the polygon cache was built from, against the current one.
    #: Equal means current, different means stale, both null means virtual. The
    #: `state` field is the readable form; these are here so a client can show
    #: *why* something is stale.
    member_hash: Optional[str] = None
    current_member_hash: Optional[str] = None

    parents: list[ParentRef] = []
    members: list[MemberRef] = []


class GraphNode(MapNode):
    """A node of the graph, as returned by `/compilations/graph`.

    One shape for compilations and ordinary maps alike, since the difference is
    a matter of flags rather than kind. The compilation-only fields are null on
    a map that has no members.
    """

    map_layer: Optional[int] = None
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    n_sources: int = 0
    assembly_mode: Optional[str] = None
    state: Optional[CompilationState] = None
    #: The layer whose faces represent this map. A served layer *is* one, so it
    #: has none of its own.
    placed_in_layer: Optional[int] = None


class GraphEdge(BaseModel):
    """One authored membership edge."""

    compilation_id: int
    member_id: int
    #: Higher wins where members overlap; null in a disjoint mosaic, where
    #: nothing overlaps and the ordering carries no meaning.
    priority: Optional[int] = None
    role: Optional[str] = None


class CompilationGraph(BaseModel):
    """The whole hierarchy, nodes and edges, in one payload.

    Small enough to hold — a few hundred of each — so a client filters, groups
    and selects locally instead of asking per level.
    """

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class NeighborMap(BaseModel):
    """Another map covering the same ground."""

    source_id: int
    slug: str
    name: Optional[str] = None
    scale: Optional[str] = None
    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    superseded_by: Optional[int] = None

    #: The neighbour's own footprint.
    area_km: Optional[float] = None
    #: Area the two footprints share. Null when the overlap was not computed —
    #: see `NeighborResult.overlap_available`.
    overlap_km: Optional[float] = None
    #: How much of *this* map the neighbour covers, 0–1. The complementary
    #: question — how much of the neighbour this map covers — is a different one,
    #: and not the one asked on a map's own page.
    overlap_fraction: Optional[float] = None

    #: Bands coarser this map is than the subject: 0 for a peer at the same
    #: scale, 1 for one band finer, and so on. Negative only when coarser maps
    #: were asked for. Rows arrive grouped by this, then by coverage.
    scale_distance: int = 0

    is_compilation: bool = False
    holds_polygons: bool = False
    is_mosaic_member: bool = False
    #: Compilations this map belongs to, so a page can say "part of SGMC" rather
    #: than leaving the reader to guess why it is in the list.
    in_compilations: list[str] = []


class NeighborResult(BaseModel):
    """Other maps of this area, and whether their overlap could be measured."""

    source_id: int
    slug: str
    #: False when the map's own boundary is too large to intersect in reasonable
    #: time, in which case every `overlap_km` is null and the list is ordered by
    #: scale distance and footprint alone.
    overlap_available: bool = True
    #: Whether maps coarser than this one were included. They are excluded by
    #: default: every map is covered by the same handful of global sheets, so
    #: listing them puts the same answers on every page.
    include_coarser: bool = False
    neighbors: list[NeighborMap] = []
