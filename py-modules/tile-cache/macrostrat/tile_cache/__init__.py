from enum import Enum


class CacheMode(str, Enum):
    prefer = "prefer"
    force = "force"
    bypass = "bypass"


class CacheStatus(str, Enum):
    hit = "hit"
    miss = "miss"
    bypass = "bypass"
