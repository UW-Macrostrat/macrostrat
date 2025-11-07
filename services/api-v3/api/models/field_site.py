from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


class Location(BaseModel):
    """
    Location model representing a geographical location with latitude and longitude.
    """

    latitude: float
    longitude: float
    elevation: Optional[float] = None
    radius: Optional[float] = None
    # A description of the location
    description: Optional[str] = None
    closest_place: Optional[str] = None
    gps_accuracy: Optional[float] = None


class IdentifiedModel(BaseModel):
    id: int


class Photo(IdentifiedModel):
    """
    A photo.
    """

    # URL at which the photo should be fetchable
    url: str
    width: int
    height: int
    checksum: str


class BeddingFacing(Enum):
    upright = "upright"
    overturned = "overturned"
    unknown = "unknown"


class PlanarOrientation(BaseModel):
    strike: float
    dip: float
    facing: BeddingFacing = BeddingFacing.upright
    notes: Optional[str] = None
    associated: list["Orientation"] = []


class LinearOrientation(BaseModel):
    plunge: float
    trend: float
    notes: Optional[str] = None


class Texture(BaseModel):
    name: str


Orientation = PlanarOrientation | LinearOrientation


class GeologicAgeInterval(IdentifiedModel):
    name: str
    t_age: Optional[float] = None
    b_age: Optional[float] = None


class Lithology(IdentifiedModel):
    name: str
    parents: Optional[list[int]] = None
    color: Optional[str] = None
    pattern: Optional[str] = None


class LithodemeType(Enum):
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
    """A lithodeme or stratigraphic unit name"""

    parent: Optional[int] = None
    type: LithodemeType
    t_interval: Optional[float] = None
    b_interval: Optional[float] = None


class RockUnit(IdentifiedModel):
    name: str
    abbreviation: Optional[str] = None
    liths: list[Lithology] = []
    age: Optional[GeologicAgeInterval] = None
    entity: Optional[LithodemeName] = None


class Fossil(IdentifiedModel):
    description: str
    taxa: Optional[str] = None


AnyData = Orientation | Photo | RockUnit | Texture | Lithology | Fossil


class Observation(BaseModel):
    notes: Optional[str] = None
    data: AnyData


class Person(IdentifiedModel):
    name: str
    email: Optional[str] = None
    orcid: Optional[str] = None
    institution: Optional[str] = None
    gravatar: Optional[str] = None


class Sample(IdentifiedModel):
    """
    A sample of a rock or sediment
    """

    name: str
    description: Optional[str] = None
    sample_type: Literal["rock", "sediment", "soil", "water"]
    igsn: Optional[str] = None
    collected: datetime


class SocialInfo(BaseModel):
    likes: int
    comments: int
    rating: Optional[int] = None


class FieldSite(BaseModel):
    """
    A site of with associated field observations
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
    children: Optional[list["FieldSite"]] = None
    contributors: Optional[list[Person]] = None
