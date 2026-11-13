"""Response models for regions.

The stored columns are still `boundary_*`; the API renames them, ahead of the
tables.
"""

from typing import Optional

from pydantic import BaseModel


class RegionSource(BaseModel):
    """The dataset a region was taken from, with its citation."""

    source_id: int
    name: Optional[str] = None
    url: Optional[str] = None
    ref_title: Optional[str] = None
    authors: Optional[str] = None
    ref_year: Optional[str] = None
    ref_source: Optional[str] = None
    isbn_doi: Optional[str] = None
    license: Optional[str] = None


class RegionSourceSummary(RegionSource):
    n_regions: int = 0


class Region(BaseModel):
    region_id: int
    source_id: int
    name: Optional[str] = None
    region_group: Optional[str] = None
    region_type: Optional[str] = None
    #: Physiographic, Basin, Glacial, ...
    region_class: Optional[str] = None
    #: West, south, east, north; absent for a region with no geometry.
    bounds: Optional[list[float]] = None


class RegionDetail(Region):
    description: Optional[str] = None
    wiki_link: Optional[str] = None
    source: Optional[RegionSource] = None
