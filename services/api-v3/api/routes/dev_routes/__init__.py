"""
This file defines all the data models used across the convert endpoints.
Think of these as blueprints that describe what a piece of data looks like,
for example what fields a photo has or what a field site contains.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel


class Location(BaseModel):
    """
    Represents a physical place on earth using latitude and longitude.
    Extra fields like elevation and GPS accuracy are optional.
    """

    latitude: float
    longitude: float
    elevation: Optional[float] = None
    radius: Optional[float] = None
    description: Optional[str] = None
    closest_place: Optional[str] = None
    gps_accuracy: Optional[float] = None


class IdentifiedModel(BaseModel):
    """
    A base model for anything that has a numeric ID.
    Other models like Photo inherit from this so they always have an id field.
    """

    id: int


class Photo(IdentifiedModel):
    """
    Represents a photo attached to a field site.
    Includes the web address where the photo can be downloaded,
    its dimensions in pixels, and a checksum for verifying file integrity.
    """

    url: str
    width: int
    height: int
    checksum: str


class BeddingFacing(Enum):
    """
    Describes which direction a rock layer is facing.
    Upright means the layer is right side up, overturned means it has been flipped.
    """

    upright = "upright"
    overturned = "overturned"
    unknown = "unknown"


class PlanarOrientation(BaseModel):
    """
    Describes the angle of a flat rock surface, like a bedding plane or fault.
    Strike is the compass direction the surface runs along.
    Dip is how steeply the surface tilts downward.
    """

    strike: float
    dip: float
    facing: BeddingFacing = BeddingFacing.upright
    notes: Optional[str] = None
    associated: list["Orientation"] = []


class LinearOrientation(BaseModel):
    """
    Describes a linear feature in a rock, like a fold axis or mineral lineation.
    Plunge is how steeply the line goes into the ground.
    Trend is the compass direction it points.
    """

    plunge: float
    trend: float
    notes: Optional[str] = None


class Texture(BaseModel):
    """
    Describes the texture or fabric of a rock, for example foliated or massive.
    """

    name: str


# An Orientation can be either a flat surface measurement or a line measurement
Orientation = PlanarOrientation | LinearOrientation


class GeologicAgeInterval(IdentifiedModel):
    """
    Represents a named time interval in geologic history, like the Jurassic.
    t age is the top (younger) boundary and b age is the bottom (older) boundary,
    both measured in millions of years.
    """

    name: str
    t_age: Optional[float] = None
    b_age: Optional[float] = None


class Lithology(IdentifiedModel):
    """
    Represents a type of rock or sediment, like sandstone or basalt.
    Parents are IDs of broader rock categories this lithology belongs to.
    """

    name: str
    parents: Optional[list[int]] = None
    color: Optional[str] = None
    pattern: Optional[str] = None


class LithodemeType(Enum):
    """
    The category of a named rock body.
    For example a Formation is a mappable rock unit, a Pluton is an igneous body.
    """

    Formation = "formation"
    Member = "member"
    Group = "group"
    Supergroup = "supergroup"
    Batholith = "batholith"
    Pluton = "pluton"
    Bed = "bed"
    Flow = "flow"
    Terrace = "terrace"
    Intrusion = "intrusion"
    ...


class LithodemeName(GeologicAgeInterval):
    """
    A named rock body such as a formation or member.
    Extends GeologicAgeInterval so it also carries age range information.
    t interval and b interval are the IDs of the bounding time intervals.
    """

    parent: Optional[int] = None
    type: LithodemeType
    t_interval: Optional[float] = None
    b_interval: Optional[float] = None


class RockUnit(IdentifiedModel):
    """
    A mappable rock unit that may contain multiple lithologies and an age range.
    Think of this as a named package of rock with known composition and age.
    """

    name: str
    abbreviation: Optional[str] = None
    liths: list[Lithology] = []
    age: Optional[GeologicAgeInterval] = None
    entity: Optional[LithodemeName] = None


class Fossil(IdentifiedModel):
    """
    Represents a fossil observation at a field site.
    Taxa is the name of the organism if it has been identified.
    """

    description: str
    taxa: Optional[str] = None


# AnyData is a union type meaning a piece of observation data can be
# any one of these recognized types
AnyData = Orientation | Photo | RockUnit | Texture | Lithology | Fossil


class Observation(BaseModel):
    """
    A single scientific observation made at a field site.
    The data field holds the actual measurement or finding,
    which could be a rock orientation, a photo, a lithology, and so on.
    """

    notes: Optional[str] = None
    data: AnyData


class Person(IdentifiedModel):
    """
    A person who contributed to field observations at a site.
    ORCID is a unique researcher identifier used in academic publishing.
    """

    name: str
    email: Optional[str] = None
    orcid: Optional[str] = None
    institution: Optional[str] = None
    gravatar: Optional[str] = None


class Sample(IdentifiedModel):
    """
    A physical sample collected from a field site, such as a rock or soil sample.
    IGSN is a global identifier for physical samples used in geoscience.
    """

    name: str
    description: Optional[str] = None
    sample_type: Literal["rock", "sediment", "soil", "water"]
    igsn: Optional[str] = None
    collected: datetime


class SocialInfo(BaseModel):
    """
    Social engagement data for a field site entry,
    tracking how many people liked or commented on it.
    """

    likes: int
    comments: int
    rating: Optional[int] = None


class FieldSite(BaseModel):
    """
    The central data model for this system.
    A FieldSite is a real location in the world where a geologist
    stopped and recorded observations. It holds all the data
    collected at that stop: location, photos, rock measurements, notes, and more.
    """

    id: int | str
    name: Optional[str] = None
    location: Location
    created: datetime
    updated: datetime
    observations: list[Observation] = []
    samples: list[Sample] = []
    photos: list[Photo] = []
    notes: Optional[str] = None
    social: Optional[SocialInfo] = None
    # Child sites allow nesting, for example a sub-stop within a larger site
    children: Optional[list["FieldSite"]] = None
    contributors: Optional[list[Person]] = None


class ImageSyncRequest(BaseModel):
    """
    The request body for the image sync endpoint.
    The caller provides the checkin to sync, both tokens for authentication,
    and StraboSpot spot ID to link the image to.
    """

    checkin_id: int
    strabo_token: str
    rockd_token: str
    spot_id: Optional[int] = None


class SyncCheckinsRequest(BaseModel):
    """
    The request body for the bulk checkin sync endpoint.
    The caller provides a list of Rockd checkins to send to StraboSpot,
    along with both tokens and the StraboSpot dataset to post the spots into.
    """

    checkins: list[dict]
    strabo_token: str
    dataset_id: int
    rockd_token: str