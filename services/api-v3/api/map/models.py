"""Response models for the map point/area queries.

The vocabulary is the one `/map/{compilation}/legend` already uses, so a client
that renders one can render the other: `map_unit_name`, `t_age`/`b_age`,
`lith_types`, and so on. What a unit adds on top of a legend entry is *where it
came from* — the map that owns the polygon, the face it sits in, and the layer
member it is presented as — which is the part the compilation system can answer
and the materialized carto tables cannot.
"""

from typing import Optional

from pydantic import BaseModel


class MapUnit(BaseModel):
    """One mapped polygon covering the requested location."""

    #: The served layer this answer came from, null when the request named a map
    #: or compilation directly rather than a layer.
    map_layer: Optional[str] = None
    #: Whether this is the layer the request's zoom would have drawn. A request
    #: against a stack gets every covering layer's answer; this marks the one
    #: that matches, without hiding the others.
    is_current_layer: bool = False
    #: The solved face the polygon's map owns here. Null outside a layer.
    map_face_id: Optional[int] = None

    map_id: int
    #: The polygon's identifier in the source dataset.
    orig_id: Optional[str] = None
    scale: Optional[str] = None

    #: The map that owns the polygon — for a mosaic member, the map whose
    #: content fills its footprint, which is not always the member itself.
    source_id: int
    source_slug: Optional[str] = None
    source_name: Optional[str] = None

    #: Rank within the layer, as the dotted path of priorities taken on the way
    #: down to this map. Higher wins where maps overlap, and comparing the paths
    #: rather than a single number is what makes "which of these two would be
    #: drawn" answerable across levels.
    priority: Optional[str] = None
    priority_path: list[int] = []
    #: The layer member this map is presented as. A face in `carto-large`
    #: belongs to member `medium` from the layer's point of view even when the
    #: map that owns it is two levels further down, and that is the level a UI
    #: should name.
    unit_id: Optional[int] = None
    unit_slug: Optional[str] = None
    unit_name: Optional[str] = None

    legend_id: Optional[int] = None
    map_unit_name: Optional[str] = None
    strat_name: Optional[str] = None
    age: Optional[str] = None
    lith: Optional[str] = None
    descrip: Optional[str] = None
    comments: Optional[str] = None
    t_age: Optional[float] = None
    b_age: Optional[float] = None
    t_interval: Optional[int] = None
    t_int_name: Optional[str] = None
    b_interval: Optional[int] = None
    b_int_name: Optional[str] = None
    color: Optional[str] = None
    lith_id: list[int] = []
    lith_types: list[str] = []
    lith_classes: list[str] = []
    strat_name_id: list[int] = []
    unit_ids: list[int] = []
