"""Response models for the compilation graph.

The vocabulary is the database's, not a second one invented here. Four facts
classify a source and there are no names for their combinations: `is_compilation`
(has members), `is_materialized` (holds polygons), `is_derived` (those polygons are
a cache cut from its members'), and `assembly_mode` (`topological` | `mosaic`). Two
more are authored: `is_served` (may be requested by name) and `superseded_by`.
`has_faces` says the compilation has faces of its own: a served one that draws
through them. The flags are derived in SQL so this module stays a description of
the payload.
"""

from typing import Literal, Optional

from pydantic import BaseModel


class MapNode(BaseModel):
    """Facts shared by every node of the graph, compilation or ordinary map."""

    source_id: int
    slug: str
    name: Optional[str] = None
    scale: Optional[str] = None

    #: Has faces of its own in `map_face`: a served compilation with a face
    #: layer -- one per scale band for a multiscale one such as `carto`. An
    #: unserved compilation has none; it is solved only within a served one.
    has_faces: bool = False
    #: May be requested by name. Authored; a compilation that is not served
    #: exists to build others.
    is_served: bool = True
    #: Bounds spanning the world: a client does not zoom to it.
    is_global: bool = False
    #: Has members.
    is_compilation: bool = False
    #: Holds polygons of its own: any ingested map, a materialized compilation,
    #: or a compilation holding originals such as SGMC.
    is_materialized: bool = False
    #: Those polygons are a cache cut from its members' -- the compilation that
    #: *replaced* its members, and can be dematerialized. False for SGMC.
    is_derived: bool = False
    #: Derived, and the members have changed since the polygons were cut.
    is_stale: bool = False
    #: Belongs to a mosaic: a real source with a citation and bounds that *are*
    #: its extent, whose content is the mosaic's inside them. No polygons,
    #: linework or faces of its own. SGMC's published maps are the case.
    is_mosaic_member: bool = False

    n_members: int = 0
    area_km: Optional[float] = None
    #: In no compilation at all — an ingested map nothing has wrapped yet. Not a
    #: kind; just a state of the catalog, and one worth showing rather than
    #: silently omitting.
    is_standalone: bool = False
    #: The map that replaced this one. Often the reason a map sits outside every
    #: compilation.
    superseded_by: Optional[int] = None


class CompilationFacts(MapNode):
    """A compilation's own state, shared by the index and the detail view."""

    #: The face layer's id for a served topological compilation. Null for a
    #: multiscale one, whose faces are per band.
    map_layer_id: Optional[int] = None
    #: The zoom band the compilation's `scale` answers for, from
    #: `map_bounds.scale_band`. `max_zoom` is null for the last band; both are
    #: null for a compilation without a scale, such as the multiscale `carto`,
    #: which answers at every zoom through its members.
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None

    #: Every map the compilation resolves to, descending through member
    #: compilations to the maps at the bottom.
    n_sources: int = 0
    assembly_mode: Optional[str] = None


class CompilationSummary(CompilationFacts):
    """A node of the compilation graph, as returned by the index."""

    #: The compilations that claim this one. Empty makes it a root of the graph.
    #: More than one is normal -- `medium` sits under both carto layers -- so
    #: this is a DAG that a client renders as a tree by repeating shared nodes.
    parent_ids: list[int] = []


class MemberRef(MapNode):
    """A map as seen from the compilation that contains it."""

    #: Higher wins where members overlap; null in a mosaic, where nothing
    #: overlaps and the ordering carries no meaning.
    priority: Optional[int] = None


class SourceRef(BaseModel):
    source_id: int
    slug: str
    name: Optional[str] = None


class ParentRef(BaseModel):
    source_id: int
    slug: str
    name: Optional[str] = None
    priority: Optional[int] = None
    has_faces: bool = False
    is_served: bool = True


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

    #: The registered compilation whose faces represent this map. Null for one
    #: that has faces of its own, and for a map that is not in the topology.
    placed_in_layer_id: Optional[int] = None

    #: The member set the polygon cache was built from, against the current one.
    #: Equal means current, different means stale, both null means virtual.
    #: `is_stale` is the readable form; these are here so a client can show
    #: *why* something is stale.
    member_hash: Optional[str] = None
    current_member_hash: Optional[str] = None

    #: The replacing map's slug, beside the inherited `superseded_by` id.
    superseded_by_slug: Optional[str] = None
    #: Maps this one supersedes -- the inverse of `superseded_by`.
    supersedes: list[SourceRef] = []
    #: `[west, south, east, north]` of the map's bounds, when it has any.
    bounds: Optional[list[float]] = None

    parents: list[ParentRef] = []
    members: list[MemberRef] = []


class GraphNode(MapNode):
    """A node of the graph, as returned by `/compilations/graph`.

    One shape for compilations and ordinary maps alike, since the difference is
    a matter of flags rather than kind. The compilation-only fields are null on
    a map that has no members.
    """

    map_layer_id: Optional[int] = None
    #: The scale's zoom band, as on `CompilationFacts`.
    min_zoom: Optional[int] = None
    max_zoom: Optional[int] = None
    n_sources: int = 0
    assembly_mode: Optional[str] = None
    #: The registered compilation whose faces represent this map. One that has
    #: faces of its own has none here.
    placed_in_layer_id: Optional[int] = None


class GraphEdge(BaseModel):
    """One authored membership."""

    compilation_id: int
    member_id: int
    #: Higher wins where members overlap; null in a mosaic, where nothing
    #: overlaps and the ordering carries no meaning.
    priority: Optional[int] = None


class CompilationGraph(BaseModel):
    """The whole hierarchy, nodes and edges, in one payload.

    Small enough to hold — a few hundred of each — so a client filters, groups
    and selects locally instead of asking per level.
    """

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class MemberEdit(BaseModel):
    """One membership as it should stand after the edit."""

    member_id: int
    priority: Optional[int] = None


class CompilationEdit(BaseModel):
    """What changes about one source. Omitted fields are left alone.

    `assembly_mode` is not editable here: it is fixed by how the compilation's
    contents were built, so changing it is restructuring, done with
    `macrostrat compilations mode`.
    """

    source_id: int
    #: The complete member list after the edit, replacing the current one: a
    #: member left out is removed, a new one added, a changed priority rewritten.
    #: Omitted, membership is untouched.
    members: Optional[list[MemberEdit]] = None
    is_served: Optional[bool] = None
    name: Optional[str] = None
    #: The map that replaces this one. Given as null, supersession is cleared;
    #: omitted, it is left alone -- so presence, not value, is what counts.
    superseded_by: Optional[int] = None


class EditRequest(BaseModel):
    """A batch of edits, applied in one transaction.

    One batch rather than a request per compilation, because a move is two
    edits -- out of one compilation, into another -- and half of one is a map
    in both places or in neither.
    """

    edits: list[CompilationEdit]
    #: Author memberships the checks would refuse (a superseded member), as
    #: `macrostrat compilations add --force` does.
    force: bool = False


class EdgeChange(BaseModel):
    compilation_id: int
    compilation_slug: str
    member_id: int
    member_slug: str
    #: `added`, `removed` or `reprioritized`.
    change: str
    priority: Optional[int] = None
    previous_priority: Optional[int] = None


class PropertyChange(BaseModel):
    source_id: int
    slug: str
    field: str
    value: Optional[str | bool | int] = None
    previous: Optional[str | bool | int] = None


class EditResult(BaseModel):
    """What the batch changed. Nothing downstream has been rebuilt:
    `macrostrat topo update` is what makes membership take effect."""

    edges: list[EdgeChange] = []
    properties: list[PropertyChange] = []


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

    #: The neighbour's own bounds.
    area_km: Optional[float] = None
    #: `overlaps` when the footprints intersect; `nearby` when they do not but
    #: this map lies within a short reach of the subject. Overlapping rows come
    #: first.
    relation: Literal["overlaps", "nearby"] = "overlaps"
    #: Roughly how much of *this* map the neighbour covers, 0–1, estimated from
    #: the two bounding boxes. Null for a nearby map.
    overlap_fraction: Optional[float] = None

    #: Bands coarser this map is than the subject: 0 for a peer at the same
    #: scale, 1 for one band finer, and so on. Negative only when coarser maps
    #: were asked for. Rows arrive grouped by this, then by coverage.
    scale_distance: int = 0

    is_compilation: bool = False
    is_materialized: bool = False
    is_mosaic_member: bool = False
    #: Whether `carto` draws this map, through any of its layers.
    in_carto: bool = False
    #: Compilations this map belongs to, so a page can say "part of SGMC" rather
    #: than leaving the reader to guess why it is in the list. Excludes carto's
    #: own layers, which `in_carto` stands for.
    in_compilations: list[str] = []


class MapMembership(BaseModel):
    """Where the subject map sits among the compilations."""

    in_carto: bool = False
    #: Carto's base layers (`small`, `medium`, `large`) the map is placed in.
    carto_layers: list[str] = []
    #: Every other compilation above the map, nearest products like `sgmc` or
    #: `ngs-bedrock` included; carto's own layers are not.
    compilations: list[SourceRef] = []


class NeighborResult(BaseModel):
    """Other maps of this area, and where this map sits among the compilations."""

    source_id: int
    slug: str
    #: Whether maps coarser than this one were included. They are excluded by
    #: default: every map is covered by the same handful of global sheets, so
    #: listing them puts the same answers on every page.
    include_coarser: bool = False
    membership: MapMembership = MapMembership()
    neighbors: list[NeighborMap] = []
